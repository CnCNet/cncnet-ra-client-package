import * as path from 'path';
import * as url from 'url';

const currentDir = path.dirname(url.fileURLToPath(import.meta.url));
const repoPath = path.resolve(currentDir, '../../');
const packagePath = path.resolve(repoPath, 'package');
const versionFilePath = path.resolve(packagePath, 'version');
const innoPath = path.resolve(currentDir, 'inno');
const innoResourcesPath = path.resolve(innoPath, 'Resources');
const setupIconPath = path.resolve(innoResourcesPath, 'cncnet5.ico');
const licenseFilePath = path.resolve(innoResourcesPath, 'License-RedAlert.txt');
const installerBinary = path.resolve(innoPath, 'bin/ISCC.exe');
const installerTemplate = path.resolve(innoPath, 'installer.twig');
const installerScript = path.resolve(innoPath, 'installer.iss');
const preUpdateExecFilename = 'preupdateexec';
const updateExecFilename = 'updateexec';
const preUpdateExecFilePath = path.resolve(packagePath, preUpdateExecFilename);
const updateExecFilePath = path.resolve(packagePath, updateExecFilename);

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
