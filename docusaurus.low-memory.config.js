import config from './docusaurus.config.js';

export default {
  ...config,
  future: {
    ...config.future,
    faster: {
      rspackBundler: false,
      rspackPersistentCache: false,
      ssgWorkerThreads: false,
    },
  },
};
