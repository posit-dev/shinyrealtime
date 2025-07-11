const esbuild = require('esbuild');

const isWatch = process.argv.includes('--watch');
const buildOptions = {
  entryPoints: ['src/index.ts'],
  bundle: true,
  minify: !isWatch,
  sourcemap: true,
  platform: 'browser',
  target: ['es2020'],
  outfile: 'www/app.js',
  format: 'iife', // Use immediately-invoked function expression for legacy compatibility
  loader: {
    '.css': 'css',
  },
};

if (isWatch) {
  esbuild.context(buildOptions)
    .then(ctx => ctx.watch())
    .then(() => console.log('Watching for changes...'))
    .catch(() => process.exit(1));
} else {
  esbuild.build(buildOptions)
    .then(() => console.log('Build complete'))
    .catch(() => process.exit(1));
}