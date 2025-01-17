from datetime import datetime
import logging


import os
import sys
import mmap
from datetime import datetime
import argparse
from typing import Optional, Tuple
import logging

class LogExtractor:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._setup_logging()

        #self._alldates()

    def _alldates(self):
        # Print first and last date
        first = False
        last = ""
        with open(self.file_path, 'r') as f:
            if not first:
                first = True
                print(f.readline()[:10])
            f.seek(0, os.SEEK_END)
            pos = f.tell() - 1
            while pos > 0 and f.read(1) != "\n":
                pos -= 1
                f.seek(pos, os.SEEK_SET)
                last = f.readline()[:10]
        print(last)
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _create_output_directory(self) -> None:
        os.makedirs('output', exist_ok=True)

    def _validate_date(self, date_str: str) -> bool:
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def _binary_search(self, mm: mmap.mmap, target_date: str) -> Tuple[Optional[int], Optional[int]]:
        file_size = len(mm)
        left = 0
        right = file_size-1

        # Binary search
        while left <= right:
            mid = (left + right) // 2
            
            # Find start of the line
            while mid > 0 and mm[mid-1:mid] != b'\n':
                mid -= 1
            
            # Read the date from the current line
            line_end = mm.find(b'\n', mid)
            if line_end == -1:
                line_end = file_size
                
            line = mm[mid:line_end].decode('utf-8')
            try:
                current_date = line[:10]
                
                if current_date < target_date:
                    left = line_end + 1
                elif current_date > target_date:
                    right = mid - 1
                else:
                    # Found matching date, now find boundaries
                    start_pos = mid
                    while start_pos > 0:
                        prev_newline = mm.rfind(b'\n', 0, start_pos - 1)
                        if prev_newline == -1:
                            break
                        prev_date = mm[prev_newline+1:prev_newline+11].decode('utf-8')
                        if prev_date != target_date:
                            break
                        start_pos = prev_newline + 1
                        
                    end_pos = line_end
                    while end_pos < file_size:
                        next_newline = mm.find(b'\n', end_pos + 1)
                        if next_newline == -1:
                            break
                        next_date = mm[end_pos+1:end_pos+11].decode('utf-8')
                        if next_date != target_date:
                            break
                        end_pos = next_newline
                        
                    return start_pos, end_pos
            except UnicodeDecodeError:
                # Handle potential decode errors by skipping corrupted sections
                self.logger.warning(f"Encountered decode error at position {mid}")
                left = line_end + 1
                
        return None, None

    def extract_logs(self, target_date: str) -> bool:
        if not self._validate_date(target_date):
            self.logger.error(f"Invalid date format: {target_date}")
            return False

        self._create_output_directory()
        output_file = f'../output/output_{target_date}.txt'
        
        try:
            with open(self.file_path, 'rb') as f:
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                
                self.logger.info(f"Searching for logs from {target_date}")
                start_pos, end_pos = self._binary_search(mm, target_date)
                
                if start_pos is None or end_pos is None:
                    self.logger.info(f"No logs found for date {target_date}")
                    return False
                
                with open(output_file, 'w') as out_f:
                    out_f.write(mm[start_pos:end_pos].decode('utf-8'))
                
                self.logger.info(f"Logs successfully extracted to {output_file}")
                mm.close()
                return True
                
        except FileNotFoundError:
            self.logger.error(f"Log file not found: {self.file_path}")
            return False
        except Exception as e:
            self.logger.error(f"Error processing logs: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Extract logs for a specific date from a large log file.')
    parser.add_argument('date')
    parser.add_argument('--file', default='../logs_2024.log')
    
    args = parser.parse_args()
    
    extractor = LogExtractor(args.file)
    success = extractor.extract_logs(args.date)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

