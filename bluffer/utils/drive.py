def drive_dir_exists(service, name):
    query = "mimeType = 'application/vnd.google-apps.folder'"
    dirs = service.files().list(q=query, pageSize=10).execute()
    items = dirs.get('files', [])
    for item in items:
        if item['name'] == name:
            return True
    return False


def get_drive_dir_id(service, name):
    query = "mimeType = 'application/vnd.google-apps.folder'"
    dirs = service.files().list(q=query, pageSize=10).execute()
    items = dirs.get('files', [])
    for item in items:
        if item['name'] == name:
            return item['id']


def get_drive_dir_url(service, name):
    drive_dir_id = get_drive_dir_id(service, name)

    folder = service.files().get(
        fileId=drive_dir_id, fields='webViewLink').execute()

    return folder.get('webViewLink')
