# Install and update with Homebrew (Mac)

Homebrew installs Better Portal and its Python dependencies. After installing, you can open the wizard from any folder with **`better-portal`**, and update with **`better-portal update`**. No Git commands or repeated ZIP downloads are needed.

This channel follows the project's **main branch**, not a numbered stable release. It does not install the macOS connection helper. A live session requires the separate signed installer and macOS approval; until that installer is released, this channel supports previews only. Homebrew never launches its Python code with sudo.

## Install once

1. If Homebrew is not installed, follow the instructions at **[brew.sh](https://brew.sh)**. Complete the installer's **Next steps**, then open a new Terminal window. `brew --version` should work. You can keep using the [ZIP installation](../README.md#get-started) if you prefer.
2. In Terminal, paste each command below and press Return:

   ```sh
   brew tap wchwawa/better-portal https://github.com/wchwawa/better-portal
   brew install --HEAD wchwawa/better-portal/better-portal
   ```

   If Homebrew asks whether to trust the formula, check that it is **wchwawa/better-portal/better-portal**, then follow its prompt. This is a community tap maintained in the Better Portal repository.
3. Open the wizard:

   ```sh
   better-portal
   ```

   Once the signed helper is installed and approved, follow the [four-step illustrated guide](../README.md#your-first-session). Without it, use `better-portal --demo` to preview the screens. Do **not** put `sudo` before this command.

Preview the screens without a password or devices with `better-portal --demo`. Check the installed revision with `better-portal --version`.

## Update

Close Better Portal and wait for any network recovery to finish. Then run:

```sh
better-portal update
```

Wait for **Update complete**, then run `better-portal` again. This command calls **`brew update`**, then **`brew upgrade --fetch-HEAD wchwawa/better-portal/better-portal`**. The `--fetch-HEAD` option is needed to check for new main-branch commits. A plain `brew upgrade` does not always check HEAD installations for new commits.

Terminal shows the old and new revision, followed by the changes included in the version actually installed. If there is no newer version, it says **Already up to date** and shows that installed version's notes again. Direct Brew installs and upgrades also display notes. You can read them again without an internet connection:

```sh
better-portal changes
```

Headings follow your saved language. Change descriptions use the original English commit subjects. Notes normally cover the changes since the previous installed revision, with a link to the exact comparison. On a first install, or if the previous revision is no longer in the project history, they are labeled **Recent changes included in this version**. Long lists are shortened with a link to the rest. These are notes from your installed package, not a possibly newer version on GitHub.

An open wizard launched through `better-portal`, or an active Mac recovery lock, prevents the update command from running. If you run Brew directly, close the wizard first. Updates do not stop a play session or repair the network for you.

If Brew reports a download or build error, read that error and retry when it is resolved. Do not run Brew with sudo. Better Portal reports failure if either Brew command fails, and keeps your settings. This wrapper disables automatic keg cleanup during the update; Brew still controls installation and dependency changes, and the wrapper does not promise an automatic rollback of every dependency.

If the error names another tap (an additional source of Brew packages), `brew update` could not refresh that source. Better Portal stops before upgrading. Fix that tap's source, then retry. Only remove a tap if you know you no longer need it; a tap pointing to a deleted local test folder can still have installed software or local commits worth keeping.

## Keep existing addresses and language

The Brew version saves settings and reports in:

```text
~/Library/Application Support/Better Portal/
```

Upgrading or removing the Brew package does not delete this folder. The old ZIP folder is left in place. The first Brew launch can ask for your addresses again because the old source installation keeps settings in that old folder.

To import them once, type **`better-portal import-settings `** in Terminal, including the final space. Drag your old **better-portal-main** folder from Finder into the Terminal window, then press Return.

Only `config.json` and `tui-settings.json` are imported. Existing Brew settings are kept; the old files are not changed or deleted. Reports remain in their original folders. Import before configuring the Brew version if you want its saved addresses and language to come from the old copy.

## Remove

Close the wizard and wait for recovery, then run:

```sh
brew uninstall better-portal
```

Your settings and reports remain available for a future installation. The source ZIP and any separately installed app are unaffected.

## For maintainers

`Formula/better-portal.rb` is the tap definition in this same repository. The custom tap URL avoids requiring a separate repository. It installs Python and a checksummed Scapy resource into an isolated virtual environment, with a stable `better-portal` entry point. The source checkout and Windows launchers keep their existing settings locations.

Keep the Scapy resource in sync with `requirements.txt`. The package must not write settings, reports or mutable state into Homebrew's Cellar. The formula bundles notes from the exact source revision at build time; write commit subjects that explain the user-visible change.

CI uses a separate disposable formula and command to test a real install, dependencies, three upgrades, repeated updates, a broken tap, a failed source fetch, retry, direct Brew notes and preservation of settings and reports through uninstall. It also opens the installed TUI before and after upgrades. The existing Better Portal command, user settings and network lock stay untouched. No test installs a root service or changes LAN settings. Run the same check on a Mac from a committed checkout with `python3 tests/integration/homebrew_lifecycle.py --log-dir /tmp/better-portal-brew-logs`.

Once numbered releases and a signed macOS app are available, a stable formula or cask can be added separately. This HEAD channel does not promise a signed app or persistent privilege approval.

Homebrew references: [maintaining a tap](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap), [Python packaging](https://docs.brew.sh/Language-Specific-Formulae), [HEAD updates](https://docs.brew.sh/Manpage#upgrade-options-installed_formulainstalled_cask-).
