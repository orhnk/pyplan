let
  # We pin to a specific nixpkgs commit for reproducibility.
  # Last updated: 2024-04-29. Check for new commits at https://status.nixos.org.
  pkgs = import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/8a4ba48accedd56f7585ccd452a47be6f80da60e.tar.gz") {};
in
  pkgs.mkShell {
    packages = with pkgs; [
      pyright
      ruff

      (python3.withPackages (pypkgs:
        with pypkgs; [
          # select Python packages here
          google-api-python-client
          google-auth-httplib2
          google-auth-oauthlib
          python-dateutil
          pytz
        ]))
    ];
  }
