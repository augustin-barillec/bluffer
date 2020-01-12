def drive_dir_exists(service, name):
    query = "mimeType = 'application/vnd.google-apps.folder'"
    dirs = service.files().list(q=query, pageSize=10).execute()
    items = dirs.get('files', [])
    for item in items:
        if item['name'] == name:
            return item['id']
    return False
