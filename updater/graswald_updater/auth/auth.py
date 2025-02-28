from abc import ABC, abstractmethod

class Authentication(ABC):
    # Simulate download
    def _sim_download_file(self, progress_handler, cancelled_event):
        self.cancel_download = False
        
        def cancel_download():
            self.cancel_download = True
            # print("CANCELLING DOWNLOAD")
        cancelled_event.add_handler(cancel_download)
        
        import time
        progress_current = 0  # Reset progress to 0
        progress_total = 100  # Set a sample total value
        for i in range(10):
            # Update the progress
            progress_current = (i + 1) * 10
            progress_handler(current=progress_current, total=progress_total)
            time.sleep(1) 
        
            if self.cancel_download:
                return False

    
    @abstractmethod
    def download_file(self, url, destination, progress_event, cancelled_event):
        """
            return progress_handler(current, total)
        """
        return NotImplementedError

    @abstractmethod
    def get_versions_info(self):
        """
            versions_info = {}
            return versions_info
        """
        return NotImplementedError
