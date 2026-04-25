import nextConfig from "eslint-config-next/core-web-vitals";

const config = [
  ...nextConfig,
  { ignores: [".next/**", "out/**"] },
];

export default config;
