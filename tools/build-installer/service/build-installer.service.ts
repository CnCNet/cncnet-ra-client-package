import { ChildProcessWithoutNullStreams, spawn } from 'child_process';
import { constants } from '../constants';
import * as Twig from 'twig';
import { access, readFile, writeFile } from 'fs';
import { TemplateModel } from '../class';
import { parse as parseIni } from 'js-ini';
import * as util from 'util';
import { resolve } from 'path';

export class BuildInstallerService {
    public static run(): void {
        new BuildInstallerService().run();
    }

    private async run(): Promise<void> {
        await this.buildInstallerScript();
        await this.buildInstaller();
    }

    private async buildInstallerScript(): Promise<void> {
        console.log('Building installer script');
        const templateModel = await this.getTemplateModel();
        console.log('Template model:');
        console.log(templateModel);
        return new Promise((resolvePromise, rejectPromise) => {
            Twig.renderFile(constants.paths.installerTemplate, templateModel, (err, content) => {
                if (err)
                    return rejectPromise(err);

                writeFile(constants.paths.installerScript, content, err => {
                    if (err)
                        return rejectPromise(err);

                    console.log(`Installer script written to '${constants.paths.installerScript}'`);

                    resolvePromise();
                });
            });
        });
    }

    private async getTemplateModel(): Promise<TemplateModel> {
        const appVersion = await this.getAppVersion();
        return {
            app: {
                name: constants.app.name,
                version: appVersion,
                versionName: `${constants.app.name} ${appVersion}`,
                publisher: constants.app.publisher,
                publisherUrl: constants.app.publisherUrl,
                supportUrl: constants.app.supportUrl,
                updatesUrl: constants.app.updatesUrl,
            },
            sourceDir: constants.paths.packagePath,
            outputDir: constants.paths.repoPath,
            setupIconFile: constants.paths.setupIconPath,
            licenseFile: constants.paths.licenseFilePath,
            outputBaseFilename: constants.outputBaseFilename,
            installDeleteFiles: await this.getInstallDeleteFiles(),
            excludedInstallerFiles: constants.excludedInstallerFiles.join(',')
        };
    }

    private async getAppVersion(): Promise<string> {
        const versionContent = await util.promisify(readFile)(constants.paths.versionFilePath, { encoding: 'utf-8' });
        const versionIni = parseIni(versionContent, {
            autoTyping: false
        });

        const sectionName = Object.keys(versionIni ?? {})[0];
        if (!sectionName)
            throw new Error(`Unable to determine version section in '${constants.paths.versionFilePath}'`);

        const section = versionIni[sectionName] as Record<string, string> | undefined;
        const version = section?.['Version']?.trim();
        if (!version)
            throw new Error(`Missing Version entry in '${constants.paths.versionFilePath}'`);

        return version;
    }

    private async getInstallDeleteFiles(): Promise<string[]> {
        const preUpdateExecDeleteFilesOrDirs = await this.getUpdateExecFileEntries(constants.paths.preUpdateExecFilePath);
        const updateExecDeleteFilesOrDirs = await this.getUpdateExecFileEntries(constants.paths.updateExecFilePath);

        const entries = [...preUpdateExecDeleteFilesOrDirs, ...updateExecDeleteFilesOrDirs];
        const uniqueEntries = Array.from(new Set(entries));

        return uniqueEntries.sort((a, b) => {
            if (a === b)
                return 0;
            return a > b ? 1 : -1;
        });
    }

    private async getUpdateExecFileEntries(file: string): Promise<string[]> {
        const content = await util.promisify(readFile)(file, {encoding: 'utf-8'});
        const ini = parseIni(content, {
            autoTyping: false,
            // tell the parser to read this as a list of strings without keys
            dataSections: ['Delete', 'DeleteFolder']
        });
        const deleteFiles = (ini['Delete'] as string[]) ?? [];
        const deleteFolders = (ini['DeleteFolder'] as string[]) ?? [];
        const rawEntries = deleteFiles.concat(deleteFolders).filter(this.isValidDeleteEntry);
        const missingEntries: string[] = [];

        await Promise.all(rawEntries.map(async entry => {
            const entryPath = resolve(constants.paths.packagePath, entry);
            try {
                await util.promisify(access)(entryPath);
                console.warn(`File in '${file}' delete list, but still in repo: '${entryPath}'`);
            } catch (error) {
                missingEntries.push(entry);
            }
        }));

        return missingEntries;
    }

    private isValidDeleteEntry(entry: string): boolean {
        return entry && entry !== 'do_not_remove_this_line';
    }

    private async buildInstaller(): Promise<void> {
        await this.ensureInstallerBinaryExists();

        const installerBinary = constants.paths.installerBinary;
        const installerScript = constants.paths.installerScript;
        const installerCwd = resolve(installerBinary, '..');

        console.log(`Building installer from script '${installerScript}'`);
        console.log(`Using Inno Setup binary '${installerBinary}'`);
        console.log(`Using working directory '${installerCwd}'`);

        await new Promise<void>((resolvePromise, rejectPromise) => {
            const startProcess = (): ChildProcessWithoutNullStreams => {
                return spawn(installerBinary, [installerScript], {
                    cwd: installerCwd,
                });
            };

            let inno: ChildProcessWithoutNullStreams;

            try {
                inno = startProcess();
            } catch (error) {
                const err = error as NodeJS.ErrnoException;
                const details = err.code ? `${err.code}: ${err.message}` : err.message;
                const fallbackCommand = `"${installerBinary}" "${installerScript}"`;
                console.warn(`Direct spawn of Inno Setup failed (${details}). Attempting shell fallback with command: ${fallbackCommand}`);
                inno = spawn(fallbackCommand, {
                    cwd: installerCwd,
                    shell: true,
                });
            }

            let stderrBuffer = '';

            inno.stdout.on('data', data => {
                console.log(data.toString());
            });

            inno.stderr.on('data', data => {
                const chunk = data.toString();
                stderrBuffer += chunk;
                console.error(chunk);
            });

            inno.on('error', error => {
                const err = error as NodeJS.ErrnoException;
                const details = err.code ? `${err.code}: ${err.message}` : err.message;
                rejectPromise(new Error(`Failed to execute Inno Setup CLI (${details}).`));
            });

            inno.on('close', code => {
                if (code !== 0) {
                    const errorMessage = stderrBuffer.trim() || 'Inno Setup CLI exited with an unknown error.';
                    return rejectPromise(new Error(`Inno Setup CLI exited with code ${code}: ${errorMessage}`));
                }

                resolvePromise();
            });
        });
    }

    private async ensureInstallerBinaryExists(): Promise<void> {
        try {
            await util.promisify(access)(constants.paths.installerBinary);
        } catch (error) {
            throw new Error(`Inno Setup binary not found at '${constants.paths.installerBinary}'. Install Inno Setup 6 or update constants.paths.installerBinary to point at ISCC.exe.`);
        }
        console.log(`Verified Inno Setup binary exists at '${constants.paths.installerBinary}'.`);
    }
}
