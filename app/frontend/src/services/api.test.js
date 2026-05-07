import { api, registerUser, loginUser, logoutUser, checkAuth, getProfileData, fetchFileTypes, getEscalation, getTrending, getTensionIndex, getPredictions, getNewsFeed, getMarketData } from './api';

// We test via the exported `api` instance by spying on its methods
beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(api, 'get').mockResolvedValue({ data: {} });
  jest.spyOn(api, 'post').mockResolvedValue({ data: {} });
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('api instance', () => {
  it('has withCredentials enabled', () => {
    expect(api.defaults.withCredentials).toBe(true);
  });

  it('has X-Requested-With header set for CSRF protection', () => {
    expect(api.defaults.headers['X-Requested-With']).toBe('XMLHttpRequest');
  });
});

describe('auth functions', () => {
  it('registerUser posts to auth/register', async () => {
    await registerUser({ email: 'a@b.com', password: '123' });
    expect(api.post).toHaveBeenCalledWith('auth/register', { email: 'a@b.com', password: '123' });
  });

  it('loginUser posts to auth/login', async () => {
    await loginUser({ email: 'a@b.com', password: '123' });
    expect(api.post).toHaveBeenCalledWith('auth/login', { email: 'a@b.com', password: '123' });
  });

  it('logoutUser posts to auth/logout', async () => {
    await logoutUser();
    expect(api.post).toHaveBeenCalledWith('auth/logout');
  });

  it('checkAuth calls GET auth/me', async () => {
    await checkAuth();
    expect(api.get).toHaveBeenCalledWith('auth/me');
  });
});

describe('data functions', () => {
  it('getProfileData calls GET profile', async () => {
    await getProfileData();
    expect(api.get).toHaveBeenCalledWith('profile', expect.any(Object));
  });

  it('fetchFileTypes calls GET file-types/', async () => {
    await fetchFileTypes();
    expect(api.get).toHaveBeenCalledWith('file-types/');
  });

  it('getNewsFeed passes limit parameter', async () => {
    await getNewsFeed(50);
    expect(api.get).toHaveBeenCalledWith('stories/map', { params: { limit: 50 } });
  });

  it('getNewsFeed uses default limit of 100', async () => {
    await getNewsFeed();
    expect(api.get).toHaveBeenCalledWith('stories/map', { params: { limit: 100 } });
  });
});

describe('analytics functions', () => {
  it('getEscalation passes hours parameter', async () => {
    await getEscalation(12);
    expect(api.get).toHaveBeenCalledWith('analytics/escalation', { params: { hours: 12 } });
  });

  it('getTrending passes hours and limit', async () => {
    await getTrending(48, 20);
    expect(api.get).toHaveBeenCalledWith('analytics/trending', { params: { hours: 48, limit: 20 } });
  });

  it('getTensionIndex uses default 24 hours', async () => {
    await getTensionIndex();
    expect(api.get).toHaveBeenCalledWith('analytics/tension', { params: { hours: 24 } });
  });

  it('getPredictions calls analytics/predictions', async () => {
    await getPredictions();
    expect(api.get).toHaveBeenCalledWith('analytics/predictions');
  });
});

describe('getMarketData', () => {
  it('returns data on success', async () => {
    api.get.mockResolvedValue({ data: { rates: { EUR: 0.92 } } });
    const result = await getMarketData();
    expect(result).toEqual({ rates: { EUR: 0.92 } });
  });

  it('returns null on failure', async () => {
    api.get.mockRejectedValue(new Error('Network error'));
    const result = await getMarketData();
    expect(result).toBeNull();
  });
});
