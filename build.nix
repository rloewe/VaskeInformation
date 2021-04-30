{ pkgs ? import <nixpkgs> {} }:


pkgs.writeScript "builder" ''
  #!${pkgs.bash}/bin/sh
  export PATH=${pkgs.binutils-unwrapped}/bin:${pkgs.openssl}:${pkgs.pkg-config}/bin:$PATH
  exec cargo build "$@"
''
