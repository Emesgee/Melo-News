import { MAX_FILE_SIZE } from '../components/upload/uploadConstants';

export const NETWORK_TIERS = {
  OFFLINE: 'offline',
  CRITICAL: 'critical',
  CONSTRAINED: 'constrained',
  NORMAL: 'normal',
};

const toPositiveNumber = (raw, fallback) => {
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

export const getConnectivityConfig = () => ({
  lowBandwidthThresholdMbps: toPositiveNumber(process.env.REACT_APP_LOW_BANDWIDTH_THRESHOLD_MBPS, 2),
  criticalBandwidthThresholdMbps: toPositiveNumber(process.env.REACT_APP_CRITICAL_BANDWIDTH_THRESHOLD_MBPS, 0.25),
  maxVideoMbCritical: toPositiveNumber(process.env.REACT_APP_MAX_VIDEO_MB_CRITICAL, 8),
  maxImageMbCritical: toPositiveNumber(process.env.REACT_APP_MAX_IMAGE_MB_CRITICAL, 2),
  maxVideoMbConstrained: toPositiveNumber(process.env.REACT_APP_MAX_VIDEO_MB_CONSTRAINED, 25),
});

export const getNetworkProfile = () => {
  const cfg = getConnectivityConfig();

  if (!navigator.onLine) {
    return {
      tier: NETWORK_TIERS.OFFLINE,
      isLowBandwidth: true,
      downlink: null,
      effectiveType: 'offline',
      saveData: false,
      reason: 'No network connection',
      thresholds: cfg,
    };
  }

  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  if (!connection) {
    return {
      tier: NETWORK_TIERS.NORMAL,
      isLowBandwidth: false,
      downlink: null,
      effectiveType: 'unknown',
      saveData: false,
      reason: 'Network API unavailable',
      thresholds: cfg,
    };
  }

  const downlink = typeof connection.downlink === 'number' ? connection.downlink : null;
  const effectiveType = connection.effectiveType || 'unknown';
  const saveData = Boolean(connection.saveData);
  const criticalByType = effectiveType === 'slow-2g' || effectiveType === '2g';
  const criticalByDownlink = downlink !== null && downlink < cfg.criticalBandwidthThresholdMbps;
  const constrainedByDownlink = downlink !== null && downlink < cfg.lowBandwidthThresholdMbps;

  let tier = NETWORK_TIERS.NORMAL;
  let reason = 'Network above threshold';

  if (saveData || criticalByType || criticalByDownlink) {
    tier = NETWORK_TIERS.CRITICAL;
    reason = saveData
      ? 'Data saver enabled'
      : criticalByType
        ? `Network type ${effectiveType}`
        : `Downlink below ${cfg.criticalBandwidthThresholdMbps} Mbps`;
  } else if (constrainedByDownlink) {
    tier = NETWORK_TIERS.CONSTRAINED;
    reason = `Downlink below ${cfg.lowBandwidthThresholdMbps} Mbps`;
  }

  return {
    tier,
    isLowBandwidth: tier === NETWORK_TIERS.CRITICAL || tier === NETWORK_TIERS.CONSTRAINED,
    downlink,
    effectiveType,
    saveData,
    reason,
    thresholds: cfg,
  };
};

export const getAdaptiveMaxFileSizeBytes = (file, profile) => {
  if (!file || !profile) return MAX_FILE_SIZE;

  const { tier, thresholds } = profile;

  if (tier === NETWORK_TIERS.CRITICAL) {
    if (file.type.startsWith('video/')) return Math.round(thresholds.maxVideoMbCritical * 1024 * 1024);
    if (file.type.startsWith('image/')) return Math.round(thresholds.maxImageMbCritical * 1024 * 1024);
  }

  if (tier === NETWORK_TIERS.CONSTRAINED && file.type.startsWith('video/')) {
    return Math.round(thresholds.maxVideoMbConstrained * 1024 * 1024);
  }

  return MAX_FILE_SIZE;
};
