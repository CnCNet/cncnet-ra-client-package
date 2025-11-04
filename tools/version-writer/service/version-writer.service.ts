import { spawn } from 'child_process';
import { constants } from '../constants';
import { rm } from 'fs/promises';
import { resolve } from 'path';

export class VersionWriterService {
    public static async run(): Promise<void> {
        await new VersionWriterService().run();
    }

    private async run(): Promise<void> {
        await new Promise<void>((resolve, reject) => {
            const versionWriter = spawn(constants.paths.versionWriterBinary, ['/S', constants.paths.packagePath], {
                cwd: __dirname,
            });

            let stderrBuffer = '';

            versionWriter.stdout.on('data', data => {
                console.log(data.toString());
            });

            versionWriter.stderr.on('data', data => {
                stderrBuffer += data.toString();
            });

            versionWriter.on('error', reject);

            versionWriter.on('close', async (code) => {
                try {
                    if (stderrBuffer) {
                        console.error(stderrBuffer.trim());
                    }

                    if (code !== 0) {
                        reject(new Error(`VersionWriter exited with code ${code}`));
                        return;
                    }

                    await this.deleteVersionWriterCopiedFiles();
                    resolve();
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    private async deleteVersionWriterCopiedFiles(): Promise<void> {
        return rm(resolve(constants.paths.packagePath, 'VersionWriter-CopiedFiles'), {
            force: true,
            recursive: true
        });
    }
}
