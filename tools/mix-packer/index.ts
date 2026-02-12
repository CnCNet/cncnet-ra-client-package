import MIXFile from "./MIXFile";
import ExFS from "./ExFS";
import * as path from "path";

import * as fs from "fs";

const inDir = path.normalize("../game-assets");
const outDir = path.normalize("../package");

const packArray = ExFS.GetPackArray(inDir);
const intermediates: string[] = [];

for (const item of packArray) {
    const parse = path.parse(item);

    let currentOutDir = path.normalize(parse.dir);
    if (!inPack(currentOutDir)) {
        currentOutDir = outDir;
    }

    ExFS.mkdir(currentOutDir);
    const mix = path.join(currentOutDir, parse.name + ".mix");
    const pack = path.join(parse.dir, parse.base);

    // Track .mix files generated inside game-assets (intermediates)
    if (currentOutDir !== outDir) {
        intermediates.push(mix);
    }

    console.log(mix);
    new MIXFile(pack).save(mix);
}

// Clean up intermediate .mix files generated inside game-assets
for (const file of intermediates) {
    if (fs.existsSync(file)) {
        fs.unlinkSync(file);
        console.log("delete " + file);
    }
}

function inPack(mixDir) {
    return (
        mixDir
            .replace(inDir, "")
            .split(path.sep)
            .findIndex((i) => i.endsWith(".pack")) !== -1
    );
}