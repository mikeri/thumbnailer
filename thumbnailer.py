import multiprocessing
import configparser
import subprocess
import mimetypes
import argparse
import logging
import pathlib
import hashlib
import os

DESCR = "Generate thumbnails on demand."
logging.basicConfig()
LOG = logging.Logger("Thumbnailer")
parser = argparse.ArgumentParser(description=DESCR)
parser.add_argument("location", help="File or directory to process")
args = parser.parse_args()


class Thumbnailer:
    def __init__(self, thumbnailer_file):
        config = configparser.ConfigParser()
        config.read(thumbnailer_file)
        LOG.debug(f"Reading thumbnailer " + thumbnailer_file)
        self.name = thumbnailer_file
        self.mime_types = config.get("Thumbnailer Entry", "MimeType").split(";")
        self.exec = config.get("Thumbnailer Entry", "Exec", raw=True)
        self.try_exec = config.get("Thumbnailer Entry", "TryExec")
        # try:
        #     subprocess.run(self.try_exec, stdout=subprocess.PIPE)
        # except Exception:
        #     LOG.error(f"TryExec for {self.try_exec} failed")
        LOG.debug(f"Registered Mime Types: " + str(self.mime_types))

    def generate_thumbnails(self, file):
        def execute(size, size_dir):
            file_uri = pathlib.Path(file).as_uri()
            out_file_name = hashlib.md5(file_uri.encode("utf-8")).hexdigest() + ".png"
            out_path = f"/home/mikeri/.thumbnails/{size_dir}/" + out_file_name
            args = self.exec.split(" ")
            new_args = []
            for arg in args:
                arg = arg.replace("%i", file)
                arg = arg.replace("%o", out_path)
                arg = arg.replace("%s", str(size))
                arg = arg.replace("%u", file_uri)
                arg = arg.replace("%%", "%")
                new_args.append(arg)
            return new_args

        subprocess.run(execute(128, "normal"), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        subprocess.run(execute(512, "large"), stderr=subprocess.PIPE, stdout=subprocess.PIPE)


def get_thumbnailers():
    thumbnailers = {}
    for thumbnailer_file in thumbnailer_files():
        thumbnailer = Thumbnailer(thumbnailer_file)
        for mime_type in thumbnailer.mime_types:
            thumbnailers[mime_type] = thumbnailer
    return thumbnailers


def thumbnailer_files():
    dirs = [
        "/usr/share/thumbnailers",
        "/usr/local/share/thumbnailers",
        os.path.expanduser("~/.local/share/thumbnailers"),
    ]
    files = []
    for _dir in dirs:
        if os.path.isdir(_dir):
            files += [
                os.path.join(_dir, f)
                for f in os.listdir(_dir)
                if os.path.isfile(os.path.join(_dir, f))
            ]
    return files


def get_mime_type(file):
    _mimetype, _ = mimetypes.guess_type(file)
    if not _mimetype:
        process = subprocess.Popen(
            ["file", "--mime-type", "-Lb", file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        mimetype, _ = process.communicate()
        _mimetype = mimetype.decode("utf-8").strip()
        if _mimetype == "application/octet-stream":
            try:
                process = subprocess.Popen(
                    ["mimetype", "--output-format", "%m", file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                mimetype, _ = process.communicate()
                _mimetype = mimetype.decode("utf-8").strip()
            except OSError:
                pass
    return _mimetype


def main():
    thumbnailers = get_thumbnailers()
    if os.path.isfile(args.location):
        mime_type = get_mime_type(args.location)
        thumbnailers[mime_type].generate_thumbnails(args.location)
    else:
        for folder, subfolders, files in os.walk(args.location):
            for file in files:
                file_path = os.path.join(os.path.abspath(folder), file)
                mime_type = get_mime_type(file_path)
                try:
                    thumbnailers[mime_type].generate_thumbnails(file_path)
                    print(f"Generated thumbnail for {file}.")
                except KeyError:
                    print(f"Skipped {file}, no thumbnailer found.")


main()
