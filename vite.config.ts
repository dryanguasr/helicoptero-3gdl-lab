import {defineConfig} from 'vite';
export default defineConfig({base:'./',build:{chunkSizeWarningLimit:5500},worker:{format:'es'}});
