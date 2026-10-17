import { cloudflareTest } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

export default defineConfig({
	plugins: [
		cloudflareTest({
			// Tests run against the production bindings (in-memory R2 bucket
			// `cerulean-docs`); preview behaviour is tested by overriding env vars.
			wrangler: { configPath: "./wrangler.jsonc", environment: "production" },
			remoteBindings: false,
		}),
	],
});
