import re
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError


def authorize_google_sheets(credentials_file):
    credentials = Credentials.from_service_account_file(credentials_file)
    service = build('sheets', 'v4', credentials=credentials)
    return service


def get_sheet_data(service, sheet_id):
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = sheet_metadata['sheets']
        return sheets
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def get_sheet_values(service, sheet_id, sheet_name):
    try:
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=sheet_name).execute()
        values = result.get('values', [])
        return values
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def get_sheet_formatting(service, sheet_id, sheet_name):
    try:
        result = service.spreadsheets().get(spreadsheetId=sheet_id, ranges=f'{sheet_name}!A:AZ',
                                            fields="sheets(data(rowData(values(userEnteredFormat))))").execute()
        return result
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def is_colored(bg_color):
    return not (
            bg_color.get('red', 1) == 1 and
            bg_color.get('green', 1) == 1 and
            bg_color.get('blue', 1) == 1
    )


def parse_skills_data(values, formatting):
    skills_data = []
    headers = values[0]
    for row_index, row in enumerate(values[1:], start=1):
        skill = row[0] if len(row) > 0 else ''
        link = row[1] if len(row) > 1 else ''
        start_date = None
        end_date = None

        for col_index in range(2, len(headers)):
            try:
                cell_format = formatting['sheets'][0]['data'][0]['rowData'][row_index]['values'][col_index][
                    'userEnteredFormat']
                if 'backgroundColor' in cell_format:
                    bg_color = cell_format['backgroundColor']
                    if is_colored(bg_color):
                        if start_date is None:
                            start_date = headers[col_index].split()[0]
                        end_date = headers[col_index].split()[0]
            except (IndexError, KeyError):
                continue

        if skill and link and start_date and end_date:
            skills_data.append((skill, link, start_date, end_date))

    return skills_data


def extract_sheet_id(sheet_url):
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    return match.group(1) if match else None


def is_valid_google_sheet_url(url):
    return bool(re.match(r"https://docs\.google\.com/spreadsheets/d/[a-zA-Z0-9-_]+", url))


def parse_google_sheet(sheet_url, credentials_file):
    if not is_valid_google_sheet_url(sheet_url):
        print("Некорректный Google Sheets URL.")
        return {}

    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        print("Failed to extract sheet ID из URL.")
        return {}

    service = authorize_google_sheets(credentials_file)
    sheets = get_sheet_data(service, sheet_id)

    skills_data = {}
    if sheets:
        for sheet in sheets:
            sheet_name = sheet['properties']['title']
            values = get_sheet_values(service, sheet_id, sheet_name)
            if values:
                formatting = get_sheet_formatting(service, sheet_id, sheet_name)
                if formatting:
                    skills = parse_skills_data(values, formatting)
                    skills_data[sheet_name] = skills
                else:
                    print(f"Failed to retrieve formatting information for sheet: {sheet_name}")
            else:
                print(f"Failed to retrieve values for sheet: {sheet_name}")
    else:
        print("Failed to retrieve sheet data.")

    return skills_data
