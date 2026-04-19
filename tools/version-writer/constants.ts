import * as path from 'path';
import * as url from 'url';

const currentDir = path.dirname(url.fileURLToPath(import.meta.url));
const versionWriterBinary = path.resolve(currentDir, 'bin/VersionWriter.exe');
const repoRoot = path.resolve(currentDir, '../../');
const packagePath = path.resolve(repoRoot, 'package');

const constants = {
    paths: {
        versionWriterBinary,
        packagePath
    }
}

export { constants };
