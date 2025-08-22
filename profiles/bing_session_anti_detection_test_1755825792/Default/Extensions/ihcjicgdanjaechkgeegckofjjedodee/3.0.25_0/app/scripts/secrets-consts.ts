// These constants will be replaced by webpack.DefinePlugin with actual environment variable values at build time
// @ts-ignore
export const HUBBLE_ACCESS_KEY = typeof HUBBLE_ACCESS_KEY_ENV !== 'undefined' ? HUBBLE_ACCESS_KEY_ENV : '';
// @ts-ignore
export const HUBBLE_SECRET_KEY = typeof HUBBLE_SECRET_KEY_ENV !== 'undefined' ? HUBBLE_SECRET_KEY_ENV : '';
