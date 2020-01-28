from __future__ import print_function
import requests
import warnings
from sys import stdout
from os import makedirs
from os.path import dirname
from os.path import exists


class GoogleDriveDownloader:
    """
    Minimal class to download shared files from Google Drive.
    https://github.com/ndrplz/google-drive-downloader
    
    Patched by Chien-Yueh Lee (kinomoto[AT]sakura[DOT]idv[DOT]tw) 
    """

    CHUNK_SIZE = 32768
    DOWNLOAD_URL = "https://docs.google.com/uc?export=download"

    @staticmethod
    def download_file_from_google_drive(file_id, dest_path, overwrite=False):
        """
        Downloads a shared file from google drive into a given folder.
        Parameters
        ----------
        file_id: str
            the file identifier.
            You can obtain it from the sherable link.
        dest_path: str
            the destination where to save the downloaded file.
            Must be a path (for example: './downloaded_file.txt')
        overwrite: bool
            optional, if True forces re-download and overwrite.
        Returns
        -------
        True/False
        """

        destination_directory = dirname(dest_path)
        if not exists(destination_directory):
            makedirs(destination_directory)

        if not exists(dest_path) or overwrite:

            session = requests.Session()

            print('Downloading {} into {}... '.format(file_id, dest_path), end='')
            stdout.flush()

            response = session.get(GoogleDriveDownloader.DOWNLOAD_URL, params={'id': file_id}, stream=True)

            token = GoogleDriveDownloader._get_confirm_token(response)
            if token:
                params = {'id': file_id, 'confirm': token}
                response = session.get(GoogleDriveDownloader.DOWNLOAD_URL, params=params, stream=True)

            if response.ok:
                GoogleDriveDownloader._save_response_content(response, dest_path)
                return True
            else:
                return False
        else:
            return False

    @staticmethod
    def _get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    @staticmethod
    def _save_response_content(response, destination):
        with open(destination, "wb") as f:
            for chunk in response.iter_content(GoogleDriveDownloader.CHUNK_SIZE):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

    def get_response(file_id):
        session = requests.Session()
        response = session.get(GoogleDriveDownloader.DOWNLOAD_URL, params={'id': file_id}, stream=True)

        token = GoogleDriveDownloader._get_confirm_token(response)
        if token:
            params = {'id': file_id, 'confirm': token}
            response = session.get(GoogleDriveDownloader.DOWNLOAD_URL, params=params, stream=True)
            
        return response
