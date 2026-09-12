# CnCNet Red Alert Client Package

<!-- <p align="center">
  <img src="package/Resources/ThemeDefault/ralogo.png" alt="Command &amp; Conquer: Red Alert" />
</p> -->

The official CnCNet [Command & Conquer: Red Alert](https://cncnet.org/red-alert) package for online play.

This package is an add-on to the [XNA CnCNet Client](https://github.com/CnCNet/xna-cncnet-client) by [Rampastring](https://github.com/Rampastring)

## Contributors

- [CCHyper](https://github.com/CCHyper)
- [Bittah Commander](https://github.com/Bittah)
- [CnCRAZER](https://github.com/CnCRAZER)
- [CO2](https://github.com/CO2-code)
- [MahBoiDeveloper](https://github.com/MahBoiDeveloper)
- [N8Diaz](https://github.com/N8Diaz)

## Used projects

- [XNA CnCNet Client](https://github.com/CnCNet/xna-cncnet-client) (GNU GPLv3 or later)
- [XNA CnCNet Client Launcher](https://github.com/CnCNet/xna-cncnet-client-launcher) (GNU GPLv3)
- [ra-patches](https://github.com/CnCNet/ra-patches) (GNU GPLv3)
- [Mobius Map Editor](https://github.com/Nyerguds/MobiusMapEditor) (GNU GPLv3 with additional terms)
- [InnoDependencyInstaller](https://github.com/DomGries/InnoDependencyInstaller) (Code Project Open License 1.02)

Additional third-party notices are included with the package and in the [installer license notice](tools/build-installer/inno/Resources/License-RedAlert.txt).

## Development

> [!IMPORTANT]
> This is not the source repository for the XNA CnCNet Client. Submit changes to the client's code upstream. If you only want to play Red Alert, use the [official CnCNet download](https://cncnet.org/red-alert) instead of cloning this repository.

Development in this repository covers the Red Alert package: maps, game assets, client configuration, update metadata, and packaging tools. Changes to the shared client or launcher belong in their upstream repositories linked above.

## Repository structure

- `package` — the distributable Red Alert client layout copied into archives and the installer.
- `game-assets` — source game assets. Directories ending in `.pack` are converted into `.mix` archives at build time.
- `tools` — Node.js, TypeScript, PowerShell, and Windows utilities for preparing, validating, building, and publishing the package.

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see https://www.gnu.org/licenses/.

Command & Conquer and Command & Conquer: Red Alert are trademarks of Electronic Arts. CnCNet is a fan project and is not affiliated with Electronic Arts.

## Sponsored by

<a href="https://www.digitalocean.com/?refcode=337544e2ec7b&utm_campaign=Referral_Invite&utm_medium=opensource&utm_source=CnCNet" title="Powered by DigitalOcean">
  <img src="https://opensource.nyc3.cdn.digitaloceanspaces.com/attribution/assets/PoweredByDO/DO_Powered_by_Badge_blue.svg" width="201" alt="Powered by DigitalOcean" />
</a>
