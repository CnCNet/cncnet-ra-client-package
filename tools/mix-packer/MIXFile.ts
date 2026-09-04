import ExBuffer from "./ExBuffer";
import ExFS from "./ExFS";
import * as path from "path";
import * as fs from "fs";

export default class MIXFile {
    folderPath: string;
    body: ExBuffer;

    includedFilesID: Map<
        number,
        {
            id: number;
            offset: number;
            size: number;
            fileName: string;
        }
    >;

    // CreateFromFolder
    constructor(folderPath: string) {
        this.folderPath = folderPath;
        this.includedFilesID = new Map();

        const filesArray = ExFS.GetFileArray(this.folderPath);

        this.body = new ExBuffer(ExFS.GetFolderSize(this.folderPath) + filesArray.length);

        for (let i = 0; i < filesArray.length; i++) {
            this.addFile(filesArray[i]);
            // console.log(i + 1, " of ", filesArray.length, "\r");
        }
    }

    addFile(filePath: string) {
        const fileName = path.basename(filePath);
        const id = MIXFile.getID(fileName);

        if (this.includedFilesID.has(id)) {
            console.log(`fileID =${id.toString(16)}, filePath =${filePath} Has in ${path}`);
            throw new Error();
        }

        const fileBuffer = ExFS.GetFile(filePath);
        const offset = this.body.findOrCopy(fileBuffer);
        const size = fileBuffer.length;

        this.includedFilesID.set(id, { id, offset, size, fileName });

        return this;
    }

    addLocalMixDatabase() {
        const fileName = "local mix database.dat";

        const fileList = Array.from(this.includedFilesID.values()).map((el) => el.fileName);
        fileList.push(fileName);
        fileList.sort();

        const body = fileList.join("\x00");
        const size = 0x34 + body.length + 1;

        const fileBuffer = Buffer.alloc(size, 0);
        fileBuffer.write("XCC by Olaf van der Spek", 0);
        // byte 0x18 is already 0x00 (null terminator) from Buffer.alloc
        Buffer.from([0x1a, 0x04, 0x17, 0x27, 0x10, 0x19, 0x80]).copy(fileBuffer, 0x19);

        fileBuffer.writeInt32LE(size, 0x20);

        fileBuffer.writeInt32LE(0x01, 0x2c); // game_ra = 1
        fileBuffer.writeInt32LE(fileList.length, 0x30);
        fileBuffer.write(body, 0x34);

        const id = MIXFile.getID(fileName);
        const offset = this.body.findOrCopy(fileBuffer);
        this.includedFilesID.set(id, { id, offset, size, fileName });

        return this;
    }

    getHeader() {
        const array = Array.from(this.includedFilesID.values());
        // RA1 engine uses signed 32-bit comparison in bsearch (compfunc casts to long)
        array.sort((a, b) => (a.id | 0) - (b.id | 0));

        const buf = new ExBuffer(array.length * 12 + 6);
        buf.offset = 6;

        for (const item of array) {
            buf.write(item.id);
            buf.write(item.offset);
            buf.write(item.size);
        }

        const result = buf.GetBuffer();
        result.writeUInt16LE(array.length, 0);
        result.writeUInt32LE(this.body.offset, 2);

        return result;
    }

    getBody() {
        return this.body.GetBuffer();
    }

    save(mixPath: string): this {
        this.addLocalMixDatabase();
        const headerBuffer = this.getHeader();
        const bodyBuffer = this.getBody();

        fs.writeFileSync(mixPath, headerBuffer);
        fs.appendFileSync(mixPath, bodyBuffer);
        return this;
    }

    // ===== statics =====
    static getID(fileName: string): number {
        fileName = fileName.toUpperCase();
        return MIXFile.rolHash(fileName, 1);
    }

    static rotateLeft(value: number, count: number): number {
        return ((value << count) | (value >>> (32 - count))) >>> 0;
    }

    static getUInt32FromBuffer(values: Uint8Array, length: number, index: {value: number}): number {
        let a = 0;
        for (let i = 0; i < 4; ++i) {
            a >>>= 8;
            if (index.value < length) {
                a += (values[index.value] << 24);
            }
            index.value++;
        }
        return a >>> 0;
    }

    static rolHash(str: string, rot: number): number {
        const values = new Uint8Array(str.length);
        for (let i = 0; i < str.length; i++) {
            values[i] = str.charCodeAt(i);
        }
        let i = 0;
        let id = 0;
        const len = values.length;
        const index = {value: 0};
        while (index.value < len) {
            const buffer = MIXFile.getUInt32FromBuffer(values, len, index);
            id = MIXFile.rotateLeft(id, rot) + buffer;
            id = id >>> 0;
        }
        return id;
    }
}