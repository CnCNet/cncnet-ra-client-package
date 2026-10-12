import { context as defaultContext } from '@actions/github';
import { AbstractRepoService } from 'cncnet-core/service';
import { existsSync, readFileSync } from 'fs';
import { program } from 'commander';
import { ReleaseAssetUploaderOptionValues } from 'cncnet-core/class';
import { resolve } from 'path';

export class ReleaseAssetUploaderService extends AbstractRepoService<ReleaseAssetUploaderOptionValues> {

    public static run(context?: typeof defaultContext | any): void {
        new ReleaseAssetUploaderService().run(context || defaultContext)
            .catch(error => {
                console.error(error);
                process.exitCode = 1;
            });
    }

    protected getOptionValues(): ReleaseAssetUploaderOptionValues {
        return ReleaseAssetUploaderOptionValues.parse();
    }

    private async run(context: any | typeof defaultContext): Promise<void> {
        const tagName = super.getTagName(context.ref);
        if (!tagName) {
            console.log('No tag/release to upload asset to');
            return;
        }
        const assetPath = this.optionValues.assetPath;
        const assetName = this.optionValues.assetName;

        console.log(`Getting release for tag ${tagName}`);
        const releaseResponse = await this.github.rest.repos.getReleaseByTag({
            owner: context.repo.owner,
            repo: context.repo.repo,
            tag: tagName
        });

        if (!releaseResponse || releaseResponse.status != 200) {
            console.error(releaseResponse);
            throw `Unable to get ID for owner: ${context.repo.owner}, repo: ${context.repo.repo}, tag: ${tagName}`;
        }

        const fullAssetPath = resolve(process.cwd(), assetPath);
        console.log(`Checking to see if asset exists at ${fullAssetPath}`);
        if (!existsSync(fullAssetPath))
            throw `Asset does not exist at: ${fullAssetPath}`;

        console.log(`Reading asset file data`);
        const data: unknown = readFileSync(fullAssetPath);

        console.log(`Uploading asset to release`);
        const uploadResponse = await this.github.rest.repos.uploadReleaseAsset({
            owner: context.repo.owner,
            repo: context.repo.repo,
            release_id: releaseResponse.data.id,
            name: assetName,
            data: data as string
        });

        if (uploadResponse.status != 201) {
            console.error(uploadResponse);
            throw `Failed to upload asset to release`;
        }

        console.log('Asset upload complete');

    }
}
