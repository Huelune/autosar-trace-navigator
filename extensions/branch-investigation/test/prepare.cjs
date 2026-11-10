// A fresh checkout has no ignored build directory. Resolve from this file, not cwd.
const fs = require('node:fs');
const path = require('node:path');
fs.mkdirSync(path.resolve(__dirname, '../../../build'), { recursive: true });
