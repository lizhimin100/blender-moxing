const fs = require('fs');

// 直接读 GLB 的 JSON chunk，看有没有 animations / skins / 层级节点
const files = process.argv.slice(2);
for (const f of files) {
  try {
    const buf = fs.readFileSync(f);
    const jsonLen = buf.readUInt32LE(12);
    const json = JSON.parse(buf.slice(20, 20 + jsonLen).toString('utf8'));
    const anims = (json.animations || []).map((a) => {
      const targets = new Set();
      (a.channels || []).forEach((c) => {
        const n = json.nodes[c.target.node];
        targets.add((n && n.name) || ('node' + c.target.node));
      });
      return { name: a.name, channels: a.channels.length, targets: [...targets].slice(0, 6) };
    });
    console.log('---', f.split(/[\\/]/).pop());
    console.log('  nodes:', (json.nodes || []).length, ' meshes:', (json.meshes || []).length,
      ' skins:', (json.skins || []).length, ' materials:', (json.materials || []).length);
    console.log('  animations:', anims.length);
    anims.forEach((a) => console.log('    ·', a.name, 'channels=', a.channels, '→', a.targets.join(', ')));
  } catch (e) {
    console.log(f, 'ERR', e.message);
  }
}
