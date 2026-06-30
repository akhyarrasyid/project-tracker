export const buildInfo = __APP_BUILD_INFO__;

export function getBuildLabel() {
  return `${buildInfo.gitSha} · ${buildInfo.version}`;
}

console.info("Project Tracker build:", buildInfo);
