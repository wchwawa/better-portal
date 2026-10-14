class BetterPortal < Formula
  include Language::Python::Virtualenv

  desc "Guided higher-bitrate setup for PlayStation Portal"
  homepage "https://github.com/wchwawa/better-portal"
  license "MIT"
  head "https://github.com/wchwawa/better-portal.git", branch: "main"

  depends_on :macos
  depends_on "python@3.14"

  resource "scapy" do
    url "https://files.pythonhosted.org/packages/df/2f/035d3888f26d999e9680af8c7ddb7ce4ea0fd8d0e01c000de634c22dcf13/scapy-2.6.1.tar.gz"
    sha256 "7600d7e2383c853e5c3a6e05d37e17643beebf2b3e10d7914dffcc3bc3c6e6c5"
  end

  def install
    odie "This revision does not include the Homebrew launcher" unless (buildpath/"portal_cli.py").exist?

    venv = virtualenv_create(libexec, "python3.14", system_site_packages: false)
    venv.pip_install resource("scapy")
    (libexec/"app").install Dir["*.py"], "locales"
    (libexec/"app/installation.json").write JSON.generate(
      version: "HEAD-#{Utils.safe_popen_read("git", "rev-parse", "--short=12", "HEAD").strip}",
      brew: HOMEBREW_PREFIX/"bin/brew",
    )
    (bin/"better-portal").write_env_script libexec/"bin/python",
                                         [(libexec/"app/portal_cli.py").to_s.shellescape], {}
  end

  def caveats
    <<~EOS
      Open the wizard: better-portal
      Update from main: better-portal update
      Preview without a password or devices: better-portal --demo

      Settings and reports stay in ~/Library/Application Support/Better Portal.
      To import existing settings: better-portal import-settings /path/to/old/folder
      Close the wizard and wait for network recovery before updating.
      Live sessions use the macOS sudo prompt; this does not install a background helper.
    EOS
  end

  test do
    assert_match "Better Portal HEAD-", shell_output("#{bin}/better-portal --version")
    system libexec/"bin/python", "-c", <<~PYTHON
      import sys
      sys.path.insert(0, #{(libexec/"app").to_s.to_json})
      import curses, portal_active_probe, portal_cli, portal_tui
      from portal_tui_text import LANGUAGES
      assert len(LANGUAGES) == 6
      from scapy.layers.l2 import Ether, ARP
      assert len(bytes(Ether()/ARP())) >= 42
    PYTHON
  end
end
