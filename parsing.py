import re
from files_util import load_json


def get_certificate_data_by_number(number, certificates):
    for _, data in certificates.items():
        metadata = data.get("onchain_metadata")

        if metadata:
            unsig_number = metadata.get("Unsig number")
            if unsig_number == f"#{str(number).zfill(5)}":
                return data   
    else:
        return None

