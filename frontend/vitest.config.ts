import { defineConfig } from 'vitest/config';
import path from 'path';

const testRoot = __dirname;
const appRoot = path.resolve(__dirname, '../../dataforge/frontend');
const appSrc = path.resolve(appRoot, 'src');
const testNodeModules = path.resolve(testRoot, 'node_modules');
const shadcn = path.resolve(appSrc, 'extensions/shadcn/components');

export default defineConfig({
  resolve: {
  dedupe: ['react', 'react-dom'],
  alias: [
    {
      find: /^react-router-dom$/,
      replacement: path.resolve(__dirname, 'test-utils/reactRouterDom.mock.ts'),
    },
    {
      find: /^sonner$/,
      replacement: path.resolve(__dirname, 'test-utils/toastMock.ts')
    },
    {
      find: /^react-i18next$/,
      replacement: path.resolve(__dirname, 'test-utils/mocks.tsx'),
    },
    {
      find: /^@\/components\/ui\/(.*)$/,
      replacement: `${shadcn}/$1`,
    },
    {
      find: /^@\/components\/(.*)$/,
      replacement: `${shadcn}/$1`,
    },
    {
      find: /^@\//,
      replacement: `${appSrc}/`,
    },
    {
      find: /^components\/(.*)$/,
      replacement: `${appSrc}/components/$1`,
    },
    {
      find: /^app\/auth$/,
      replacement: path.resolve(__dirname, 'test-utils/appAuth.mock.ts'),
    },
    {
      find: /^app$/,
      replacement: path.resolve(__dirname, 'test-utils/app.mock.ts')
    },
    {
      find: /^app\/(.*)$/,
      replacement: `${appSrc}/app/$1`,
    },
  ],
    },
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: './setup.ts',
        include: ['**/integration/*.test.tsx'],
  },
});