import os
import subprocess
import argparse
from pathlib import Path
import json
import shutil
from rich.console import Console, Group
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.text import Text
import logging
import concurrent.futures
import configparser

console = Console()

# Default settings
DEFAULT_INPUT_DIR = r"C:\Anime"
DEFAULT_OUTPUT_DIR = r"C:\output"
DEFAULT_MKVEXTRACT_PATH = r"C:\Program Files\MKVToolNix\mkvextract.exe"

class MKVExtractor:
    def __init__(self, config):
        self.config = config
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            TimeRemainingColumn()
        )
        self.layout = Layout()
        self.layout.split(
            Layout(name="progress"),
            Layout(name="log")
        )
        self.log_content = []
        self.max_log_history = 30  # Keep 30 lines of history
        self.live = Live(self.layout, refresh_per_second=4)
        self.results = []
        self.setup_logging()
        self.current_directory = None
        self.file_counter = [0, 0]  # [current, total]

    def setup_logging(self):
        log_file = Path(__file__).parent / 'mkv_extractor.log'
        logging.basicConfig(filename=log_file, level=logging.ERROR,
                            format='%(asctime)s - %(levelname)s - %(message)s')

    def log(self, message):
        self.log_content.append(message)
        self.log_content = self.log_content[-self.max_log_history:]
        self.update_display()

    def update_display(self):
        progress_panel = Panel(
            Group(
                self.progress,
                Text(f"Current file: {self.file_counter[0]} of {self.file_counter[1]}", justify="right", style="cyan")
            ),
            title="Extraction Progress",
            border_style="green",
            expand=True
        )
        self.layout["progress"].update(progress_panel)

        log_height = self.layout["log"].size.height if self.layout["log"].size else 10
        available_lines = max(1, log_height - 2)  # Subtract 2 for panel borders

        if len(self.log_content) > available_lines:
            visible_log_content = self.log_content[-available_lines:]
        else:
            padding = [''] * (available_lines - len(self.log_content))
            visible_log_content = padding + self.log_content

        log_panel = Panel(
            "\n".join(visible_log_content),
            title="Log",
            subtitle=f"Current directory: {self.current_directory}" if self.current_directory else "",
            border_style="yellow",
            expand=True
        )
        self.layout["log"].update(log_panel)

    def get_mkv_info(self, file_path, mkvmerge_path):
        cmd = [mkvmerge_path, '-J', str(file_path)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            self.log(f"Error running mkvmerge: {e}")
            logging.error(f"Error running mkvmerge on file {file_path}: {e}")
            return None
        except json.JSONDecodeError as e:
            self.log(f"Error parsing mkvmerge output: {e}")
            logging.error(f"Error parsing mkvmerge output for file {file_path}: {e}")
            return None

    def get_subtitle_extension(self, codec, name):
        codec = codec.lower()
        name = name.lower()
        
        if 'ass' in codec or 'ssa' in codec or 'ass' in name:
            return 'ass'
        elif 'srt' in codec or 'subrip' in codec or 'srt' in name:
            return 'srt'
        elif 'vobsub' in codec:
            return 'idx'
        elif 'pgs' in codec or 'hdmv_pgs' in codec:
            return 'sup'
        elif 'dvbsub' in codec:
            return 'dvbsub'
        else:
            logging.warning(f"Unknown subtitle codec: {codec}, name: {name}. Defaulting to .sub")
            return 'sub'

    def extract_mkv(self, file_path, output_dir, mkvextract_path, mkvmerge_path, file_task):
        info = self.get_mkv_info(file_path, mkvmerge_path)
        if not info:
            return "Failed to get MKV info"

        extract_cmds = []
        extracted_items = []

        # Extract chapters
        if info.get('chapters'):
            chapter_file = os.path.join(output_dir, 'chapters', f"{Path(file_path).stem}_chapters.xml")
            os.makedirs(os.path.dirname(chapter_file), exist_ok=True)
            extract_cmds.extend(['chapters', chapter_file])
            extracted_items.append('Chapters')

        # Extract subtitles
        for track in info.get('tracks', []):
            if track['type'] == 'subtitles':
                codec = track.get('codec', '')
                name = track.get('properties', {}).get('codec_id', '')
                ext = self.get_subtitle_extension(codec, name)
                track_name = track.get('properties', {}).get('track_name', '')
                track_name_suffix = f"[{track_name}]" if track_name else ""
                sub_file = os.path.join(output_dir, 'subs', f"{Path(file_path).stem}_track{track['id']}{track_name_suffix}.{ext}")
                os.makedirs(os.path.dirname(sub_file), exist_ok=True)
                extract_cmds.extend(['tracks', f"{track['id']}:{sub_file}"])
                extracted_items.append(f'Subtitle ({codec}, {ext})')

        # Extract fonts
        for attachment in info.get('attachments', []):
            mime_type = attachment.get('content_type', '').lower()
            if any(font_type in mime_type for font_type in ['font', 'application/x-truetype-font', 'application/x-font-ttf', 'application/vnd.ms-opentype']):
                font_file = os.path.join(output_dir, 'fonts', attachment['file_name'])
                os.makedirs(os.path.dirname(font_file), exist_ok=True)
                extract_cmds.extend(['attachments', f"{attachment['id']}:{font_file}"])
                extracted_items.append(f"Font ({attachment['file_name']})")

        if not extract_cmds:
            return "No extractable content found"

        cmd = [mkvextract_path, str(file_path)] + extract_cmds
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    if "Progress:" in output:
                        progress = int(output.split(":")[1].strip().rstrip("%"))
                        self.progress.update(file_task, completed=progress)

            returncode = process.poll()
            if returncode == 0:
                self.progress.update(file_task, completed=100)
                return f"Extracted: {', '.join(extracted_items)}"
            else:
                error = process.stderr.read()
                logging.error(f"Error extracting file {file_path}: {error}")
                return f"Error extracting: {error}"
        except Exception as e:
            logging.error(f"Exception during extraction of {file_path}: {str(e)}")
            return f"Error: {str(e)}"

    def copy_info_file(self, input_dir, output_dir):
        try:
            info_file = next(input_dir.glob('info.txt'), None)
            if info_file:
                output_dir.mkdir(parents=True, exist_ok=True)  # Ensure output directory exists
                dest_file = output_dir / info_file.name
                shutil.copy2(info_file, dest_file)
                self.log(f"Copied info.txt to {dest_file}")
        except Exception as e:
            self.log(f"Error copying info.txt: {str(e)}")
            logging.error(f"Error copying info.txt from {input_dir} to {output_dir}: {str(e)}")

    def process_file(self, file, input_dir, output_dir, mkvextract_path, mkvmerge_path):
        rel_path = file.parent.relative_to(input_dir)
        file_output_dir = output_dir / rel_path
        
        if file.parent != self.current_directory:
            self.current_directory = file.parent
            self.log(f"Processing directory: {self.current_directory}")
            self.copy_info_file(file.parent, file_output_dir)
        
        file_task = self.progress.add_task(file.name, total=100, visible=True)
        self.log(f"Processing file: {file.name}")
        
        try:
            result = self.extract_mkv(file, file_output_dir, mkvextract_path, mkvmerge_path, file_task)
            self.results.append([file.name, result])
        except Exception as e:
            logging.error(f"Error processing file {file}: {str(e)}")
            self.results.append([file.name, f"Error: {str(e)}"])
        
        self.progress.remove_task(file_task)
        self.file_counter[0] += 1
        self.update_display()

    def process_directory(self, input_dir, output_dir, mkvextract_path, mkvmerge_path):
        mkv_files = list(Path(input_dir).rglob('*.mkv'))
        self.file_counter = [0, len(mkv_files)]
        
        self.log(f"Found {len(mkv_files)} MKV files to process")
        overall_task = self.progress.add_task("Overall Progress", total=len(mkv_files))
        
        use_parallel = self.config.getboolean('Settings', 'use_parallel', fallback=False)
        max_workers = self.config.getint('Settings', 'max_workers', fallback=os.cpu_count())

        if use_parallel:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_file, file, input_dir, output_dir, mkvextract_path, mkvmerge_path) for file in mkv_files]
                for future in concurrent.futures.as_completed(futures):
                    future.result()  # This will raise any exceptions that occurred
                    self.progress.update(overall_task, advance=1)
        else:
            for file in mkv_files:
                self.process_file(file, input_dir, output_dir, mkvextract_path, mkvmerge_path)
                self.progress.update(overall_task, advance=1)

    def display_results(self):
        table = Table(title="Extraction Results")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="magenta")
        for result in self.results:
            table.add_row(result[0], result[1])
        console.print(table)

    def run(self, args):
        with self.live:
            self.log("Starting MKV Extractor")
            
            input_dir = Path(args.input_dir or self.config.get('Paths', 'input_dir', fallback=DEFAULT_INPUT_DIR))
            output_dir = Path(args.output_dir or self.config.get('Paths', 'output_dir', fallback=DEFAULT_OUTPUT_DIR))
            mkvextract_path = args.mkvextract_path or self.config.get('Paths', 'mkvextract_path', fallback=DEFAULT_MKVEXTRACT_PATH)
            mkvmerge_path = str(Path(mkvextract_path).parent / "mkvmerge")
            
            if not Path(mkvextract_path).exists():
                self.log("Error: mkvextract not found. Please install mkvtoolnix or provide the correct path.")
                return
            
            if not input_dir.is_dir():
                self.log(f"Error: Input directory '{input_dir}' does not exist.")
                return
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            self.log(f"Input directory: {input_dir}")
            self.log(f"Output directory: {output_dir}")
            self.log(f"mkvextract path: {mkvextract_path}")
            
            self.process_directory(input_dir, output_dir, mkvextract_path, mkvmerge_path)
            
            self.log("MKV Extraction completed")

        self.display_results()

def load_config():
    config = configparser.ConfigParser()
    config_path = Path(__file__).parent / 'mkv_extractor_config.ini'
    if config_path.exists():
        config.read(config_path)
    else:
        # Create default config
        config['Paths'] = {
            'input_dir': DEFAULT_INPUT_DIR,
            'output_dir': DEFAULT_OUTPUT_DIR,
            'mkvextract_path': DEFAULT_MKVEXTRACT_PATH
        }
        config['Settings'] = {
            'use_parallel': 'false',
            'max_workers': str(os.cpu_count()),
            'max_log_lines': '1000'
        }
        with open(config_path, 'w') as configfile:
            config.write(configfile)
    return config

def main():
    config = load_config()
    
    parser = argparse.ArgumentParser(description="Extract chapters, subtitles, and fonts from MKV files.")
    parser.add_argument("--input_dir", help="Input directory containing MKV files")
    parser.add_argument("--output_dir", help="Output directory for extracted files")
    parser.add_argument("--mkvextract_path", help="Path to mkvextract executable")
    args = parser.parse_args()

    extractor = MKVExtractor(config)
    extractor.run(args)

if __name__ == "__main__":
    main()
