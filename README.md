# gallery-dl Desktop

An unofficial Windows app powered by [gallery-dl](https://codeberg.org/mikf/gallery-dl) and [yt-dlp](https://github.com/yt-dlp/yt-dlp). Save images and videos from supported sites or extract images from individual web pages.

## Install on Windows

Choose **one** method. Both require 64-bit Windows 10/11, an internet connection, WinGet, and Google Chrome, Microsoft Edge, or Brave. Setup uses the browser already installed on your PC.

### Option 1 — Windows installer (.exe)

1. Open [Releases → latest](https://github.com/raffaele-pet/gallery-dl-Desktop/releases/latest) and download **`gallery-dl-Desktop-Setup.exe`** under **Assets**.
2. Run the EXE. Dependency progress appears in the Setup window.
3. Open **gallery-dl Desktop** from the Start menu or the optional desktop shortcut.

To update an existing EXE installation, run the latest installer and choose **Update**. Setup also detects older desktop shortcuts. If you used a ZIP, select its folder in Setup to update in place. If you used Git, Setup can copy your settings and browser session into the EXE installation while keeping the checkout available.

### Option 2 — From the repository

1. Use **Code → Download ZIP** and extract it, or clone the repository.

   ```sh
   git clone https://github.com/raffaele-pet/gallery-dl-Desktop.git
   ```

2. Open the extracted or cloned folder and run **`INSTALL.bat`**.
3. Open the **gallery-dl Desktop** shortcut or run **`RUN.vbs`**.

## Use

Paste one or more URLs, choose **Save to** and **Collection name**, select **Images**, **Videos**, or both, then click **Download**. The progress bar follows the current file when its size or segment count is available. Open **Show details** for saved files and diagnostics.

**Images** is selected by default. The app reuses any existing localized media folders. Choose **One folder** to keep images and videos together.

For Instagram, sign in through the browser window if prompted. Sessions are kept locally in `.browser-profile`; keep this folder private. Site access restrictions still apply.

## Update and troubleshoot

- For EXE installations, use **Tools → Check for app updates** to find the latest installer or **Update download engines** to refresh gallery-dl and yt-dlp.
- For repository installations, use **Tools → Update app and engines** or rerun `INSTALL.bat` to check and update required tools.
- Use `INSTALL.bat --check` for a read-only requirements check.
- Use `RUN_DEBUG.cmd` if the app does not start.

Download only content you are authorized to save.
