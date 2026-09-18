# CnCNet Red Alert Client Package

![logo](package/Resources/logo.png)

The official CnCNet [Red Alert](https://cncnet.org/red-alert) package for online play.
This package is an add-on to the [XNA CnCNet Client](https://github.com/CnCNet/xna-cncnet-client) by [Rampastring](https://github.com/Rampastring)

## Contributors

- [CCHyper](https://github.com/CCHyper)
- [Bittah Commander](https://github.com/Bittah)
- [CnCRAZER](https://github.com/CnCRAZER)
- [CO2](https://github.com/CO2-code)
- [MahBoiDeveloper](https://github.com/MahBoiDeveloper)
- [N8Diaz](https://github.com/N8Diaz)
- [RaVaGe](https://github.com/CnC-RaVaGe)

## Used projects

- [XNA CnCNet Client](https://github.com/CnCNet/xna-cncnet-client) (GNU GPLv3 or later)
- [XNA CnCNet Client Launcher](https://github.com/CnCNet/xna-cncnet-client-launcher) (GNU GPLv3)
- [ra-patches](https://github.com/CnCNet/ra-patches) (GNU GPLv3)
- [Mobius Map Editor](https://github.com/Nyerguds/MobiusMapEditor) (GNU GPLv3 with additional terms)

## Development

> [!IMPORTANT]
> This is not the source repository for the XNA CnCNet Client. Submit changes to the client's source code [upstream](https://github.com/CnCNet/xna-cncnet-client). This is simply a configuration for it.

Development in this repository covers the Red Alert package: maps, game assets, client configuration, update metadata, and packaging tools. Changes to the shared client or launcher belong in their upstream repositories linked above.

## Repository structure

- `package` - the exact file structure that should make up the client package that is delivered to users.
- `game-assets` - source game assets from freeware version. Directories ending in `.pack` are converted into `.mix` archives at build time.
- `tools` - tools that are used to help build the package.

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see https://www.gnu.org/licenses/.

## Legal

EA has not endorsed and does not support this product. Command & Conquer, Command & Conquer: Red Alert, Command & Conquer: Red Alert: Counterstrike, Command & Conquer: Red Alert: The Aftermath, Command & Conquer: Red Alert: Retaliation are registered trademarks of Electronic Arts Inc. All Rights Reserved.

## Sponsored by

<a href="https://www.digitalocean.com/?refcode=337544e2ec7b&utm_campaign=Referral_Invite&utm_medium=opensource&utm_source=CnCNet" title="Powered by DigitalOcean">
  <img src="https://opensource.nyc3.cdn.digitaloceanspaces.com/attribution/assets/PoweredByDO/DO_Powered_by_Badge_blue.svg" width="201" alt="Powered by DigitalOcean" />
</a>
