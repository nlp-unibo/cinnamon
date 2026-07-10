import logging
import tarfile
from pathlib import Path
from typing import Optional, Tuple
from urllib.request import urlretrieve

import pandas as pd
from tqdm import tqdm

from cinnamon.component import Component


class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_url(download_path: Path, url: str):
    with DownloadProgressBar(
        unit="B", unit_scale=True, miniters=1, desc=url.split("/")[-1]
    ) as t:
        urlretrieve(url, filename=download_path, reporthook=t.update_to)


class IMDBLoader(Component):
    def __init__(
        self,
        download_directory: Path,
        download_filename: str,
        dataset_name: str,
        download_url: str,
        samples_amount: int = -1,
    ):
        self.download_directory = download_directory
        self.download_filename = download_filename
        self.dataset_name = dataset_name
        self.download_url = download_url
        self.samples_amount = samples_amount

        self.download_path = download_directory.joinpath(download_filename)
        self.extraction_path = self.download_path.parents[0]
        self.dataframe_path = self.extraction_path.joinpath(dataset_name)

    def download(self):
        if not self.download_directory.exists():
            self.download_directory.mkdir(parents=True)

        # Download
        if not self.download_path.exists():
            download_url(url=self.download_url, download_path=self.download_path)

            # Extract
            with tarfile.open(self.download_path) as loaded_tar:
                loaded_tar.extractall(self.extraction_path)

        # Clean
        if self.download_path.exists():
            self.download_path.unlink()

    def read_df_from_files(self) -> pd.DataFrame:
        dataframe_rows = []
        for split in ["train", "test"]:
            for sentiment in ["pos", "neg"]:
                folder = self.extraction_path.joinpath("aclImdb", split, sentiment)
                for filepath in folder.glob("**/*"):
                    if not filepath.is_file():
                        continue

                    filename = filepath.name
                    with filepath.open(mode="r", encoding="utf-8") as text_file:
                        text = text_file.read()
                        score = filename.split("_")[1].split(".")[0]
                        file_id = filename.split("_")[0]

                        # create single dataframe row
                        dataframe_row = {
                            "file_id": file_id,
                            "score": score,
                            "sentiment": sentiment,
                            "split": split,
                            "text": text,
                        }
                        dataframe_rows.append(dataframe_row)

        df = pd.DataFrame(dataframe_rows)
        df = df[["file_id", "score", "sentiment", "split", "text"]]
        df = df.rename(columns={"sentiment": "y", "text": "x"})

        # Save dataframe for quick retrieval
        df.to_csv(path_or_buf=self.dataframe_path, index=None)

        return df

    def load_data(self) -> pd.DataFrame:
        if not self.dataframe_path.is_file():
            logging.info("First time loading dataset...Downloading...")
            self.download()
            df = self.read_df_from_files()
        else:
            if self.dataframe_path.is_file():
                logging.info("Loaded pre-loaded dataset...")
                df = pd.read_csv(self.dataframe_path)
            else:
                logging.info(
                    "Couldn't find pre-loaded dataset...Building dataset from files..."
                )
                df = self.read_df_from_files()
                df.to_csv(self.dataframe_path, index=False)

        return df

    def get_splits(
        self,
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        df = self.load_data()
        train = (
            df[df.split == "train"]
            .sample(frac=1)
            .reset_index(drop=True)[: self.samples_amount]
        )
        val = None
        test = (
            df[df.split == "test"]
            .sample(frac=1)
            .reset_index(drop=True)[: self.samples_amount]
        )

        return train, val, test
