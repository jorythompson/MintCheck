import sys
import thompco_utils
from configparser import ConfigParser
import os


class ConfigManager:
    def __init__(self, file_name, create=False):
        self.file_name = file_name
        self.config = ConfigParser()
        self.config.optionxform = str
        self.create = create
        if not create:
            self.config.read(file_name)
        self.notes = []

    @staticmethod
    def missing_entry(section, entry, file_name, default_value=None):
        logger = thompco_utils.get_logger()
        logger.debug("starting")
        if default_value is None:
            log_fn = logger.critical
            message = "Required entry"
            default_value = ""
        else:
            log_fn = logger.debug
            message = "Entry"
            if default_value == "":
                default_value = "Ignoring."
            else:
                default_value = "Using default value of (" + str(default_value) + ")"
        log_fn(message + " \"" + entry + "\" in section [" + section + "] in file: " + file_name
               + " is malformed or missing.  " + str(default_value))
        if default_value == "":
            log_fn("Exiting now")
            sys.exit()

    @staticmethod
    def _insert_note(lines, line_number, note):
        if "\n" in note["notes"]:
            message = note["notes"].split("\n")
        else:
            message = note["notes"]
        if type(message) == str:
            lines.insert(line_number, "# " + message + ":\n")
        else:
            for l in message[:-1]:
                lines.insert(line_number, "# " + l + "\n")
                line_number += 1
            lines.insert(line_number, "# " + message[-1] + ":\n")

    def read_entry(self, section, entry, default_value, value_type, notes=None):
        value = None
        if self.create:
            try:
                self.config.add_section(section)
            except Exception as e:
                pass
            if notes is not None:
                self.notes.append({"section": section,
                                   "entry": entry,
                                   "notes": notes})
            self.config.set(section, entry, str(default_value))
        else:
            try:
                if value_type is str:
                    value = self.config.get(section, entry)
                elif value_type is int:
                    value = self.config.getint(section, entry)
                elif value_type is float:
                    value = self.config.getfloat(section, entry)
                elif value_type is bool:
                    value = self.config.getboolean(section, entry)
                else:
                    print("type not handled for ()".format(value_type))
            except Exception:
                ConfigManager.missing_entry(section, entry, self.file_name, default_value)
        return value

    def read_section(self, section, default_entries, notes=None):
        key_values = None
        if self.create:
            try:
                self.config.add_section(section)
            except Exception as e:
                pass
            for entry in default_entries:
                self.config.set(section, str(entry), default_entries[entry])
            if notes is not None:
                self.notes.append({"section": section,
                                   "entry": None,
                                   "notes": notes})
        else:
            key_values = dict()
            for (key, val) in self.config.items(section):
                key_values[key] = val
        return key_values

    def write(self, out_file):
        if os.path.isfile(out_file):
            print("File {} exists!  You must remove it before running this".format(out_file))
        #    sys.exit()
        f = open(out_file, "w")
        self.config.write(f)
        f.close()
        f = open(out_file)
        lines = f.readlines()
        f.close()
        for note in self.notes:
            in_section = False
            line_number = 0
            for line in lines:
                if "[" + note["section"] + "]" in line:
                    if note["entry"] is None:
                        ConfigManager._insert_note(lines, line_number, note)
                        break
                    else:
                        in_section = True
                elif line.startswith("[") and line.endswith("]"):
                    in_section = False
                if in_section:
                    if line.startswith(note["entry"]):
                        ConfigManager._insert_note(lines, line_number, note)
                        break
                line_number += 1
        f = open(out_file, "w")
        contents = "".join(lines)
        f.write(contents)
        f.close()
        print("Done writing {}".format(out_file))
        sys.exit()
