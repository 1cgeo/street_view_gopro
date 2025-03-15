import webbrowser
import os

chrome_path = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'

ULTIMA_IMG = 'MULTICAPTURA_1784_001392'

ignore = True
metadados = os.listdir('./METADATA_CAMPO_NOVO')
for i, metadata in enumerate(sorted(metadados)):
    image = metadata.split('.')[0]
    if image == ULTIMA_IMG:
        ignore = False
    if ignore:
        continue
    webbrowser.get(chrome_path).open(f'http://localhost:10000/?image={image}')
    input(f"Press Enter to continue... {i}")
