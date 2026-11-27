import * as THREE from 'three';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { OrbitControls } from './vendor/OrbitControls.js';

// ================================================================== 参数
// b=<id>       指定初始建筑（交互模式）
// shot=<id>    单帧校验模式：加载后停在 anim/t 指定的一帧，但依然可交互
// anim / t     指定 clip 与时间
// yaw / zoom   指定初始方位角与取景倍率
// flat=1       法线材质（几何校验）
// debug=1      HUD 打印渲染统计
const Q = new URLSearchParams(location.search);
const SHOT = Q.get('shot');
const STILL = !!SHOT;                    // 只影响“是否自动播放”，绝不影响渲染循环

const S = {
  manifest: null,
  entry: null,
  root: null,
  mixer: null,
  actions: {},
  clip: null,
  action: null,
  playing: !STILL,
  loop: !STILL,
  speed: 1,
  team: new THREE.Color('#b8352c'),
  team2: new THREE.Color('#ffe08a'),
  teamOn: 1,
  time: 0,
  stages: [],
  busy: false,
};

const TEAMS = [
  { name: '血红', c: '#b8352c', g: '#ffcf7a' },
  { name: '钴蓝', c: '#2f5fb0', g: '#9fd0ff' },
  { name: '苔绿', c: '#4a7a34', g: '#c2e88a' },
  { name: '紫晶', c: '#6b3fa0', g: '#d9b6ff' },
  { name: '琥珀', c: '#c98a1e', g: '#ffe6a3' },
];

const $ = (id) => document.getElementById(id);

// ================================================================== 渲染器
const main = document.querySelector('main');
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
let DPR = Math.min(devicePixelRatio || 1, 2);
renderer.setPixelRatio(DPR);
renderer.setSize(main.clientWidth, main.clientHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.42;
renderer.outputColorSpace = THREE.SRGBColorSpace;
main.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color('#171b22');
scene.fog = new THREE.Fog('#1a1f26', 160, 460);

const camera = new THREE.PerspectiveCamera(38, main.clientWidth / main.clientHeight, 0.3, 300);
camera.position.set(12, 9, 20);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.075;
controls.rotateSpeed = 0.85;
controls.zoomSpeed = 0.9;
controls.minDistance = 0.8;
controls.maxDistance = 220;
controls.maxPolarAngle = Math.PI * 0.495;
controls.screenSpacePanning = true;
controls.target.set(0, 2, 0);
controls.update();

// ---------- 环境探针（金属需要有内容可反射）
function buildEnv() {
  const c = document.createElement('canvas');
  c.width = 16; c.height = 64;
  const g = c.getContext('2d');
  const grad = g.createLinearGradient(0, 0, 0, 64);
  grad.addColorStop(0.0, '#f4f7ff');
  grad.addColorStop(0.36, '#c8d2e2');
  grad.addColorStop(0.50, '#9ba6b8');
  grad.addColorStop(0.64, '#6d7688');
  grad.addColorStop(0.82, '#474e5c');
  grad.addColorStop(1.0, '#2d323c');
  g.fillStyle = grad; g.fillRect(0, 0, 16, 64);
  const tex = new THREE.CanvasTexture(c);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  const pmrem = new THREE.PMREMGenerator(renderer);
  const env = pmrem.fromEquirectangular(tex).texture;
  pmrem.dispose();
  return env;
}
scene.environment = buildEnv();
scene.environmentIntensity = 1.05;

// ---------- 灯光
// v2 §1.4：主光固定屏幕左上方 45°，阴影统一投向右下
const key = new THREE.DirectionalLight('#fff3dd', 3.3);
key.position.set(-10.5, 14, -8.5);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.near = 1;
key.shadow.camera.far = 46;
const sc = 13;
key.shadow.camera.left = -sc; key.shadow.camera.right = sc;
key.shadow.camera.top = sc; key.shadow.camera.bottom = -sc;
key.shadow.bias = -0.0006;
key.shadow.normalBias = 0.02;
scene.add(key);

// 补光改中性：原来偏蓝，石头会被染成青灰色，是"网游感"的主要来源
const fill = new THREE.DirectionalLight('#c8cdd4', 0.6);
fill.position.set(8, 5, 7);
scene.add(fill);

const rim = new THREE.DirectionalLight('#ffe3c2', 0.68);
rim.position.set(4, 6, -13);
scene.add(rim);

scene.add(new THREE.HemisphereLight('#c6c8c4', '#46412f', 1.2));

// ---------- 地面
const groundMat = new THREE.MeshStandardMaterial({ color: '#3b4232', roughness: 0.94, metalness: 0.0 });
const ground = new THREE.Mesh(new THREE.PlaneGeometry(900, 900), groundMat);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

const grid = new THREE.GridHelper(120, 120, '#4a5340', '#2f362a');
grid.material.transparent = true;
grid.material.opacity = 0.45;
grid.position.y = 0.001;
scene.add(grid);

// ================================================================== 阵营染色
const U = { team: { value: S.team }, team2: { value: S.team2 }, on: { value: S.teamOn } };

function patchMaterial(mat, emissiveTeam) {
  const orm = mat.roughnessMap || mat.metalnessMap || mat.aoMap || null;
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uTeamColor = U.team;
    shader.uniforms.uTeamColor2 = U.team2;
    shader.uniforms.uTeamOn = U.on;
    shader.uniforms.uORM = { value: orm };
    shader.uniforms.uEmiTeam = { value: emissiveTeam ? 1 : 0 };

    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform vec3 uTeamColor; uniform vec3 uTeamColor2;
        uniform float uTeamOn; uniform float uEmiTeam;
        uniform sampler2D uORM;`)
      .replace('#include <map_fragment>', `#include <map_fragment>
        {
          float tc = texture2D(uORM, vMapUv).a * uTeamOn;
          if (tc > 0.002) {
            float lum = dot(diffuseColor.rgb, vec3(0.2126, 0.7152, 0.0722));
            vec3 dyed = uTeamColor * (0.30 + 0.95 * lum);
            diffuseColor.rgb = mix(diffuseColor.rgb, dyed, clamp(tc, 0.0, 1.0));
          }
        }`)
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
        {
          float e = length(totalEmissiveRadiance);
          totalEmissiveRadiance += uTeamColor2 * e * uEmiTeam * 2.0;
        }`);
  };
  mat.needsUpdate = true;
}

// ================================================================== 载入 / 释放
const loader = new GLTFLoader();
let token = 0;

function disposeMaterial(m) {
  ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'emissiveMap', 'alphaMap']
    .forEach((k) => m[k]?.dispose?.());
  m.dispose?.();
}

function disposeRoot(root) {
  root.traverse((o) => {
    if (o.isSkinnedMesh && o.skeleton) o.skeleton.dispose?.();
    if (o.geometry) o.geometry.dispose();
    const mats = Array.isArray(o.material) ? o.material : (o.material ? [o.material] : []);
    mats.forEach(disposeMaterial);
  });
}

function clearView() {
  if (S.root) {
    scene.remove(S.root);
    disposeRoot(S.root);
    S.root = null;
  }
  S.mixer = null;
  S.actions = {};
  S.action = null;
  S.clip = null;
}

function toast(msg, sticky) {
  const el = $('loading');
  if (!el) return;
  if (!msg) { el.style.display = 'none'; return; }
  el.style.display = 'flex';
  el.textContent = msg;
  if (!sticky) {
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.style.display = 'none'; }, 2600);
  }
}

// ================================================================== 视图装配
function fitCamera(box, yawDeg, zoom) {
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const zf = zoom || 1.16;
  const vFov = (camera.fov * Math.PI) / 180;
  const hFov = 2 * Math.atan(Math.tan(vFov / 2) * Math.max(camera.aspect, 0.2));

  // 底部时间轴与顶部 HUD 会盖住画面，按"可用高度"折算，避免建筑被裁脚
  const barH = ($('track')?.closest('.tl')?.offsetHeight || 96) + 34;
  const usable = Math.min(1, Math.max(0.55,
    (main.clientHeight - barH) / Math.max(main.clientHeight, 1)));

  const dv = (size.y / 2) / Math.tan(vFov / 2) / usable;
  const dh = (Math.max(size.x, size.z) / 2) / Math.tan(hFov / 2);
  const dist = Math.max(dv, dh) * zf + Math.max(size.x, size.z) * 0.32;

  // 目标点略微下移 → 建筑在画面里整体上移，让出时间轴
  controls.target.copy(center);
  controls.target.y -= size.y * 0.05;

  const yaw = (yawDeg != null ? yawDeg : 214) * Math.PI / 180;
  const pitch = 0.30;
  camera.position.set(
    center.x + Math.sin(yaw) * dist * Math.cos(pitch),
    center.y + Math.sin(pitch) * dist,
    center.z - Math.cos(yaw) * dist * Math.cos(pitch)
  );
  camera.near = Math.max(0.3, dist / 900);
  camera.far = Math.max(300, dist * 8);
  camera.updateProjectionMatrix();
  controls.update();
}

function buildAnimList(clips) {
  const host = $('anims');
  host.innerHTML = '';
  clips.forEach((c) => {
    const el = document.createElement('div');
    el.className = 'an';
    el.dataset.clip = c.name;
    el.innerHTML = `<span>${c.name}</span><em>${c.duration.toFixed(2)}s</em>`;
    el.onclick = () => playClip(c.name);
    host.appendChild(el);
  });
}

function playClip(name) {
  const a = S.actions[name];
  if (!a) return;
  Object.values(S.actions).forEach((x) => x.action.stop());
  S.clip = a.clip;
  S.action = a.action;
  a.action.reset();
  a.action.setLoop(S.loop ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
  a.action.clampWhenFinished = !S.loop;
  a.action.timeScale = S.speed;
  a.action.play();
  S.time = 0;
  S.playing = !STILL;
  $('btnPlay').textContent = S.playing ? '暂停' : '播放';
  document.querySelectorAll('.an').forEach((e) => e.classList.toggle('on', e.dataset.clip === name));
  $('tlName').textContent = name.toUpperCase();
  $('hitmark').style.display = 'none';
  $('hitlab').style.display = 'none';
  $('hBadge').textContent = name === 'build' ? 'CONSTRUCTION'
    : name === 'destroy' ? 'DESTRUCTION' : 'BIND POSE';
  updateTL(true);
}

function buildStageBar() {
  const bar = $('stagebar');
  const ticks = $('ticks');
  bar.innerHTML = ''; ticks.innerHTML = '';
  if (!S.stages.length) { bar.style.display = 'none'; ticks.style.display = 'none'; return; }
  bar.style.display = 'flex'; ticks.style.display = 'block';
  const dur = (S.actions.build?.clip.duration) || 4.8;
  S.stages.forEach((st) => {
    const d = document.createElement('div');
    d.textContent = st.name;
    d.dataset.stage = st.stage;
    d.onclick = () => seekStage(st);
    bar.appendChild(d);
    const t = document.createElement('div');
    t.className = 'tick';
    t.style.left = (st.t0 / dur * 100) + '%';
    ticks.appendChild(t);
  });
}

function seekStage(st) {
  const build = S.actions.build;
  if (!build) return;
  if (S.clip?.name !== 'build') playClip('build');
  const a = S.actions.build.action;
  a.paused = true;
  S.playing = false;
  $('btnPlay').textContent = '播放';
  S.clip = S.actions.build.clip;
  S.action = a;
  const tgt = Math.min(st.t0 + 0.05, S.clip.duration - 0.02);
  a.time = tgt;
  S.mixer.update(0);
  S.time = tgt;
  updateTL(true);
}

async function select(entry) {
  if (!entry) return;
  const my = ++token;
  S.busy = true;
  toast('正在装配 ' + entry.cn + ' …', true);

  try {
    const gltf = await loader.loadAsync(entry.glb);
    if (my !== token) { disposeRoot(gltf.scene); return; }   // 期间又点了别的

    clearView();

    const root = gltf.scene;
    root.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      o.receiveShadow = true;
      o.frustumCulled = false;                 // 蒙皮包围盒不可靠，避免视角一变就消失
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      mats.forEach((m) => {
        m.envMapIntensity = 0.6;
        m.roughness = Math.min(1, m.roughness * 1.08);
        ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'emissiveMap']
          .forEach((k) => { if (m[k]) m[k].channel = 1; });
        const nm = (m.name || '').toLowerCase();
        patchMaterial(m, nm.includes('emblem'));
      });
    });

    scene.add(root);
    S.root = root;
    S.entry = entry;

    S.mixer = new THREE.AnimationMixer(root);
    S.actions = {};
    (gltf.animations || []).forEach((clip) => {
      const a = S.mixer.clipAction(clip);
      a.setLoop(THREE.LoopRepeat, Infinity);
      S.actions[clip.name] = { action: a, clip };
    });

    const box = new THREE.Box3().setFromObject(root);
    fitCamera(box, Q.get('yaw') ? parseFloat(Q.get('yaw')) : 214,
              parseFloat(Q.get('zoom') || '') || 1.16);

    buildAnimList(gltf.animations || []);

    const first = (gltf.animations || []).find((c) => c.name === 'static')
      || (gltf.animations || [])[0];
    if (first) playClip(first.name);

    // 单帧模式：切到指定 clip / 时间并暂停
    if (STILL) {
      const cn = Q.get('anim');
      if (cn && S.actions[cn]) playClip(cn);
      const t = parseFloat(Q.get('t') || '0');
      if (S.action) {
        S.action.paused = true;
        S.action.time = Math.min(t, S.clip.duration);
        S.mixer.update(0);
        S.time = S.action.time;
      }
      S.playing = false;
      $('btnPlay').textContent = '播放';
    }

    $('hBadge').textContent = 'ASSET';
    $('hTitle').textContent = entry.cn;
    S.stages = entry.stage_times || [];
    buildStageBar();
    updateSub();
    const b = box.getSize(new THREE.Vector3());
    S.footBase = `SIZE  ${b.x.toFixed(2)} × ${b.y.toFixed(2)} × ${b.z.toFixed(2)} m`;
    $('foot').textContent = S.footBase;

    // 高亮当前建筑
    document.querySelectorAll('.mod').forEach((e) => e.classList.toggle('on', e.dataset.id === entry.id));

    toast(null);
    updateTL(true);

    // three 的着色器程序缓存在同一会话内跨建筑复用，新材质首帧可能命中上一座建筑的
    // 程序变体（表现为屋面竖面过曝成白条）。首帧渲染后强制重编译一次即可消除。
    requestAnimationFrame(() => {
      if (S.root !== root) return;
      root.traverse((o) => {
        if (!o.isMesh) return;
        const ms = Array.isArray(o.material) ? o.material : [o.material];
        ms.forEach((m) => { m.needsUpdate = true; });
      });
    });

    if (STILL) document.title = 'READY';
  } catch (err) {
    console.error(err);
    toast('加载失败：' + (err?.message || err), true);
  } finally {
    if (my === token) S.busy = false;
  }
}

function updateSub() {
  const e = S.entry;
  if (!e) return;
  const parts = [e.id.toUpperCase()];
  if (e.triangles) parts.push((e.triangles / 1000).toFixed(0) + 'K TRIS');
  if (e.height) parts.push(e.height.toFixed(2) + ' m');
  if (e.materials != null) parts.push(e.materials + ' MAT');
  if (e.draw_calls != null) parts.push(e.draw_calls + ' DC');
  parts.push(`${Object.keys(S.actions).length} CLIPS`);
  $('hSub').textContent = parts.join('  ·  ');
}

// ================================================================== 时间轴
let lastTL = { p: -1, label: '', stage: -1 };

function updateTL(force) {
  if (!S.clip) return;
  const p = Math.min(1, Math.max(0, S.time / S.clip.duration));

  if (force || Math.abs(p - lastTL.p) > 0.0015) {
    lastTL.p = p;
    $('fill').style.width = (p * 100) + '%';
    $('clk').style.left = (p * 100) + '%';
    $('tlTime').textContent = `${S.time.toFixed(2)} / ${S.clip.duration.toFixed(2)}s`;
  }

  let label = '';
  if (S.clip.name === 'build' && S.stages.length) {
    const st = S.stages.find((x) => S.time >= x.t0 && S.time <= x.t1);
    if (st) label = '▸ ' + st.name;
  }
  if (force || label !== lastTL.label) {
    lastTL.label = label;
    $('tlInfo').textContent = label;
  }

  if (S.clip.name === 'build' && S.stages.length) {
    const active = S.stages.findIndex((x) => S.time >= x.t0 && S.time <= x.t1 + 0.25);
    if (force || active !== lastTL.stage) {
      lastTL.stage = active;
      document.querySelectorAll('#stagebar div').forEach((d, i) => {
        const st = S.stages[i];
        d.classList.toggle('on', i === active);
        d.classList.toggle('done', st && S.time > st.t1 + 0.25);
      });
    }
  }
}

// ================================================================== UI
function buildSidebar() {
  const host = $('buildings');
  host.innerHTML = '';
  S.manifest.buildings.forEach((e) => {
    const el = document.createElement('div');
    el.className = 'mod';
    el.dataset.id = e.id;
    el.innerHTML = `<b>${e.cn}</b><span>${e.id}</span>`;
    el.onclick = () => { if (!S.busy || S.entry?.id !== e.id) select(e); };
    host.appendChild(el);
  });

  const t = $('teams');
  t.innerHTML = '';
  TEAMS.forEach((tc, i) => {
    const el = document.createElement('div');
    el.className = 'sw' + (i === 0 ? ' on' : '');
    el.style.background = tc.c;
    el.title = tc.name;
    el.onclick = () => {
      document.querySelectorAll('.sw').forEach((x) => x.classList.remove('on'));
      el.classList.add('on');
      S.team.set(tc.c); U.team.value = S.team;
      S.team2.set(tc.g); U.team2.value = S.team2;
    };
    t.appendChild(el);
  });
}

$('tint').oninput = (e) => {
  S.teamOn = +e.target.value;
  U.on.value = S.teamOn;
  $('tv').textContent = S.teamOn.toFixed(2);
};

$('spd').oninput = (e) => {
  S.speed = +e.target.value;
  $('sv').textContent = S.speed.toFixed(2) + '×';
  if (S.action) S.action.timeScale = S.speed;
};

$('btnPlay').onclick = () => {
  S.playing = !S.playing;
  $('btnPlay').textContent = S.playing ? '暂停' : '播放';
  if (S.action) S.action.paused = !S.playing;
};

$('btnLoop').onclick = () => {
  S.loop = !S.loop;
  $('btnLoop').textContent = '循环 ' + (S.loop ? '开' : '关');
  if (S.action) {
    S.action.setLoop(S.loop ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
    S.action.clampWhenFinished = !S.loop;
  }
};

$('dbgWire').onchange = (e) => {
  if (!S.root) return;
  S.root.traverse((o) => {
    if (!o.isMesh) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    mats.forEach((m) => { m.wireframe = e.target.checked; });
  });
};
$('dbgGrid').onchange = (e) => { grid.visible = e.target.checked; };
$('dbgShadow').onchange = (e) => {
  ground.visible = e.target.checked;
  key.castShadow = e.target.checked;
};

// 时间轴拖拽
const track = $('track');
let scrubbing = false;
const seek = (e) => {
  if (!S.clip) return;
  const r = track.getBoundingClientRect();
  const p = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
  S.time = p * S.clip.duration;
  if (S.action) {
    S.action.time = S.time;
    if (S.mixer) S.mixer.update(0);
  }
  updateTL(true);
};
track.addEventListener('pointerdown', (e) => {
  scrubbing = true;
  track.setPointerCapture(e.pointerId);
  seek(e);
});
track.addEventListener('pointermove', (e) => { if (scrubbing) seek(e); });
track.addEventListener('pointerup', () => { scrubbing = false; });
track.addEventListener('pointercancel', () => { scrubbing = false; });

// 键盘：空格暂停 / ←→ 单步 / 1-6 切建筑
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;
  if (e.code === 'Space') { e.preventDefault(); $('btnPlay').click(); }
  else if (e.code === 'ArrowLeft' || e.code === 'ArrowRight') {
    if (!S.clip) return;
    e.preventDefault();
    const d = (e.code === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 1 / 30 : 0.1);
    S.time = Math.min(S.clip.duration, Math.max(0, S.time + d));
    if (S.action) { S.action.time = S.time; S.action.paused = true; S.playing = false; $('btnPlay').textContent = '播放'; }
    S.mixer?.update(0);
    updateTL(true);
  } else if (/^Digit[1-6]$/.test(e.code)) {
    const i = +e.code.slice(5) - 1;
    const e2 = S.manifest?.buildings[i];
    if (e2) select(e2);
  }
});

// ================================================================== 主循环
const clock = new THREE.Clock();
let frames = 0, acc = 0, slowStreak = 0;

function tick() {
  requestAnimationFrame(tick);

  const dt = Math.min(clock.getDelta(), 0.1);

  if (S.mixer && S.action && S.playing && !S.action.paused) {
    S.mixer.update(dt * S.speed);
    S.time = S.clip ? (S.action.time % S.clip.duration) : 0;
    updateTL(false);
  }

  controls.update();
  renderer.render(scene, camera);

  // 自适应像素比：连续掉帧就降一档，避免高 DPI 下卡成幻灯片
  frames++;
  acc += dt;
  if (acc >= 1) {
    const fps = frames / acc;
    if (fps < 40 && DPR > 1) {
      slowStreak++;
      if (slowStreak >= 2) {
        DPR = Math.max(1, DPR * 0.75);
        renderer.setPixelRatio(DPR);
        renderer.setSize(main.clientWidth, main.clientHeight);
        slowStreak = 0;
      }
    } else {
      slowStreak = 0;
    }
    if (S.footBase) {
      $('foot').textContent = S.footBase + '\n' + fps.toFixed(0) + ' FPS' +
        (DPR < Math.min(devicePixelRatio || 1, 2) - 0.01 ? '  ·  DPR ' + DPR.toFixed(2) : '');
    }
    frames = 0; acc = 0;
  }
}

// ================================================================== 自适应尺寸
function onResize() {
  camera.aspect = main.clientWidth / Math.max(main.clientHeight, 1);
  camera.updateProjectionMatrix();
  renderer.setSize(main.clientWidth, main.clientHeight);
}
addEventListener('resize', onResize);
if (window.ResizeObserver) new ResizeObserver(onResize).observe(main);

// ================================================================== 启动
(async () => {
  tick();                                   // 循环先跑起来，空场景也能交互

  const res = await fetch('../assets/_历史版本/万邦_v5/manifest.json?v=' + Date.now());
  if (!res.ok) throw new Error('manifest ' + res.status + ' — 请用 HTTP 打开，不要双击文件');
  S.manifest = await res.json();
  buildSidebar();

  const want = Q.get('b') || SHOT;
  const entry = S.manifest.buildings.find((x) => x.id === want) || S.manifest.buildings[0];
  await select(entry);

  if (Q.get('flat')) {
    S.root?.traverse((o) => {
      if (o.isMesh) o.material = new THREE.MeshNormalMaterial({ side: THREE.DoubleSide });
    });
  }
  if (Q.get('debug')) {
    $('hSub').textContent += `  |  ${renderer.info.render.calls} CALLS  ${renderer.info.render.triangles} TRIS`;
  }
})().catch((err) => {
  console.error(err);
  toast('启动失败：' + (err?.message || err), true);
});

// 调试句柄（控制台可用，方便排查与自动化校验）
window.__preview = {
  S, camera, controls, renderer, scene, select,
  // 便于截图/校验：重新按当前画面比例取景
  fit(yawDeg, zoom) {
    if (!S.root) return;
    const b = new THREE.Box3().setFromObject(S.root);
    fitCamera(b, yawDeg != null ? yawDeg : 214, zoom || 1.0);
  },
};
