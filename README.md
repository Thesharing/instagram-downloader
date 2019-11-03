# Instagram Downloader

Download and archive all your saved posts in your instagram using selenium and requests.

## Install and Run

```bash
pip install -r requirements.txt
```

Download chromedriver.exe from https://chromedriver.chromium.org/downloads. The version of chromedriver.exe must be corresponding to the version of Google Chrome.

Use Google Chrome to login Instagram and get the cookie from Developer Tools (F12).

Save the cookie to cookie.txt.

Change the username in `spider.get_saved_list('<Your Username>')`.

Run `main.py`.

## Todo

* Add comments and documents.
* Simplify the logic