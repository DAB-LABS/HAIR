import json from "@rollup/plugin-json";
import resolve from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";
import terser from "@rollup/plugin-terser";

export default {
    input: "src/ha-panel-ir-devices.ts",
    output: {
        file: "dist/ha-panel-ir-devices.js",
        format: "es",
        sourcemap: false,
    },
    plugins: [
        json(),
        resolve({ browser: true }),
        typescript({ tsconfig: "./tsconfig.json" }),
        terser({
            format: { comments: false },
            compress: { passes: 2 },
        }),
    ],
};
