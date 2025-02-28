import requests

from .auth import Authentication


class HTTPS(Authentication):

    def __init__(self, url, headers={}):
        super().__init__()
        self.url = url
        self.headers = headers

    def download_file(self, url, destination, progress_event, cancelled_event):
        # print("Called HTTPS File download!")

        self.cancel_download = False

        def cancel_download():
            self.cancel_download = True
            # print("CANCELLING DOWNLOAD")

        cancelled_event.add_handler(cancel_download)

        try:
            response = requests.get(url, headers=self.headers, stream=True)
            response.raise_for_status()  # Raise an exception if the request was not successful

            if ("application/json" in response.headers.get("content-type")):
                try:
                    json_data = response.json()
                    if ("downloadUrl" in json_data["data"].keys()):
                        url = json_data["data"]["downloadUrl"]
                        response = requests.get(url, headers=self.headers, stream=True)
                        response.raise_for_status()  # Raise an exception if the request was not successful
                except Exception:# as e:
                    # print(f"Error occurred while trying to get download url: {str(e)}")
                    ...

            # Start File download
            total_size = int(response.headers.get("content-length", 0))
            self.progress_total = total_size
            self.progress_current = 0  # Reset progress to 0

            with open(destination, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    file.write(chunk)
                    self.progress_current += len(chunk)
                    progress_event(current=self.progress_current, total=self.progress_total)
                    if self.cancel_download:
                        return False
                self.progress_urrent = self.progress_total
            # print("Download complete!")
        except requests.exceptions.RequestException:# as e:
            # print(f"Error occurred while downloading file: {str(e)}")
            ...

    def get_versions_info(self):
        try:
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()  # Raise an exception if the request was not successful

            if ("application/json" not in response.headers.get("content-type")):
                return None

            json_data = response.json()
            if ("data" not in json_data.keys()):
                return None

            if ("downloadUrl" in json_data["data"].keys()):
                url = json_data["data"]["downloadUrl"]
                # print(url)
                response = requests.get(url, headers=self.headers, stream=True)
                response.raise_for_status()  # Raise an exception if the request was not successful
                json_data = response.json()
                if ("data" in json_data.keys()):
                    versions = json_data['data']
            else:
                versions = json_data["data"]
            return versions
        except requests.exceptions.RequestException:# as e:
            # print(f"Error occurred while downloading file: {str(e)}")
            ...
