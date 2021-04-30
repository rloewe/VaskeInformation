{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    pkgs.pkgconfig
    pkgs.binutils
    pkgs.openssl
  ];
}
