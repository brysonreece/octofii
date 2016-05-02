# coding=utf-8
from __future__ import absolute_import
import os
import octoprint.plugin
import yagmail

class OctofiiPlugin(octoprint.plugin.EventHandlerPlugin,
                          octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.TemplatePlugin):
	
	#~~ SettingsPlugin

	def get_settings_defaults(self):
		# matching password must be registered in system keyring
		# to support customizable mail server, may need port too
		return dict(
			enabled=False,
			recipient_name="",
			recipient_address="",
			mail_server="",
			mail_username="",
			mail_useralias="",
			include_snapshot=True,
			printStarted_message=dict(
				title="Print job started",
				body="Dear {recipient_name}, your file ({filename}) has started printing."
			),
			printDone_message=dict(
				title="Print job complete",
				body="Dear {recipient_name}, {filename} done printing after {elapsed_time}."
			),
			printCancelled_message=dict(
				title="Print job failed",
				body="Dear {recipient_name}, {filename} has encountered errors resulting in a failed print."
			)
		)
	
	def get_settings_version(self):
		return 1

	#~~ TemplatePlugin

	def get_template_configs(self):
		return [
			dict(type="settings", name="Octofii", custom_bindings=False)
		]

	#~~ EventPlugin
	
	def on_event(self, event, payload):
		if event not in ["PrintDone", "PrintStarted", "PrintFailed", "PrintCancelled"]:
			return
		
		if not self._settings.get(['enabled']):
			return
		
		filename = os.path.basename(payload["file"])
		
		import datetime
		import octoprint.util
		elapsed_time = octoprint.util.get_formatted_timedelta(datetime.timedelta(seconds=payload["time"]))
		recipient_name = self._settings.get(['recipient_name'])
		
		tags = {'filename': filename, 'elapsed_time': elapsed_time, 'recipient_name': recipient_name}

		if event == "PrintStarted":
			title = self._settings.get(["printStarted_message", "title"]).format(**tags)
			message = self._settings.get(["printStarted_message", "body"]).format(**tags)
		elif event == "PrintDone":
			title = self._settings.get(["printDone_message", "title"]).format(**tags)
			message = self._settings.get(["printDone_message", "body"]).format(**tags)
		elif event in ["PrintCancelled", "PrintFailed"]:
			title = self._settings.get(["printCancelled_message", "title"]).format(**tags)
			message = self._settings.get(["printCancelled_message", "body"]).format(**tags)
		
		content = [message]
		
		if self._settings.get(['include_snapshot']):
			snapshot_url = self._settings.globalGet(["webcam", "snapshot"])
			if snapshot_url:
				try:
					import urllib
					filename, headers = urllib.urlretrieve(snapshot_url)
				except Exception as e:
					self._logger.exception("Snapshot error (sending email notification without image): %s" % (str(e)))
				else:
					content.append({filename: "snapshot.jpg"})
		
		try:
			mailer = yagmail.SMTP(user={self._settings.get(['mail_username']):self._settings.get(['mail_useralias'])}, host=self._settings.get(['mail_server']))
			emails = [email.strip() for email in self._settings.get(['recipient_address']).split(',')]
			mailer.send(to=emails, subject=title, contents=content, validate_email=False)
		except Exception as e:
			# report problem sending email
			self._logger.exception("Email notification error: %s" % (str(e)))
		else:
			# report notification was sent
			self._logger.info("Print notification emailed to %s" % (self._settings.get(['recipient_address'])))		

	def get_update_information(self):
		return dict(
			octofii=dict(
				displayName="Octofii Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="brysonreece",
				repo="octofii",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/brysonreece/octofii/archive/{target_version}.zip",
				dependency_links=False
			)
		)

__plugin_name__ = "Octofii"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = OctofiiPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

