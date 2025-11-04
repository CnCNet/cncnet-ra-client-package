import { resolve } from 'path';

const repoPath = resolve(__dirname, '../../');
const packagePath = resolve(repoPath, 'package');
const versionFilePath = resolve(packagePath, 'version');
const innoPath = resolve(__dirname, 'inno');
const innoResourcesPath = resolve(innoPath, 'Resources');
// Use the game's executable as the installer icon to ensure a valid icon resource for Inno Setup
const setupIconPath = resolve(packagePath, 'RedAlert.exe');
const licenseFilePath = resolve(innoResourcesPath, 'License-RedAlert.txt');
const installerBinary = resolve(innoPath, 'bin/ISCC.exe');
const installerTemplate = resolve(innoPath, 'installer.twig');
const installerScript = resolve(innoPath, 'installer.iss');
const preUpdateExecFilename = 'preupdateexec';
const updateExecFilename = 'updateexec';
const preUpdateExecFilePath = resolve(packagePath, preUpdateExecFilename);
const updateExecFilePath = resolve(packagePath, updateExecFilename);

const constants = {
    app: {
        name: 'CnCNet Red Alert',
        publisher: 'cncnet.org',
        publisherUrl: 'https://cncnet.org',
        supportUrl: 'https://cncnet.org',
        updatesUrl: 'https://cncnet.org'
    },
    outputBaseFilename: 'CnCNet5_RA_Installer',
    paths: {
        installerBinary,
        installerTemplate,
        installerScript,
        repoPath,
        packagePath,
        setupIconPath,
        licenseFilePath,
        versionFilePath,
        preUpdateExecFilePath,
        updateExecFilePath
    },
    excludedInstallerFiles: [
        preUpdateExecFilename,
        updateExecFilename,
        'versionconfig.ini',
        'REDALERT.ini'
    ]
}
export { constants };
