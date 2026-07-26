# import pandas as pd


# class ExcelExtractor:

#     def __init__(self):
#         pass

#     def extract(self, excel_files):

#         documents = []

#         for file in excel_files:

#             print(f"Reading {file}")

#             sheets = pd.read_excel(file, sheet_name=None)

#             for sheet_name, df in sheets.items():

#                 df = df.fillna("")

#                 for index, row in df.iterrows():

#                     text = ""

#                     for column in df.columns:
#                         text += f"{column}: {row[column]}\n"

#                     documents.append(
#                         {
#                             "text": text.strip(),

#                             "metadata": {

#                                 "file": file,

#                                 "sheet": sheet_name,

#                                 "row": index + 2
#                             }
#                         }
#                     )

#         return documents


import pandas as pd

class ExcelExtractor:

    def extract(self, excel_files):

        documents = []

        for file in excel_files:

            sheets = pd.read_excel(file, sheet_name=None)

            for sheet_name, df in sheets.items():

                df = df.fillna("")

                for idx, row in df.iterrows():

                    text = "\n".join(
                        [f"{col}: {row[col]}" for col in df.columns]
                    )

                    documents.append({

                        "text": text,

                        "metadata": {

                            "file": file,

                            "sheet": sheet_name,

                            "row": idx + 2

                        }

                    })

        return documents