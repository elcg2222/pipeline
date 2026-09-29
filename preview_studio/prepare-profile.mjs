import {existsSync, copyFileSync} from 'node:fs';
const active = new URL('./src/active-profile.json', import.meta.url);
if (!existsSync(active)) copyFileSync(new URL('./src/sample-profile.json', import.meta.url), active);
