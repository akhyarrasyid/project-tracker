export const buildInfo = __APP_BUILD_INFO__;

export function getBuildLabel() {
  return "Project Tracker v1.00";
}

console.info("Project Tracker build:", buildInfo);
