class Sessionport < Formula
  include Language::Python::Virtualenv

  desc "Carry your AI agent sessions between CLIs"
  homepage "https://github.com/Reality-Shifting-Tech/sessionport"
  url "https://files.pythonhosted.org/packages/source/s/sessionport/sessionport-0.3.0.tar.gz"
  sha256 "8cd681b28e67fc60edf7314ebc962034ccc854243db1cae132e0ed7f4d992ed8"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "sessionport", shell_output("#{bin}/sessionport version")
  end
end
