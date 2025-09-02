import { getDict } from '../dictionary';

describe('getDict', () => {
  test('returns French labels', () => {
    const dict = getDict('fr');
    expect(dict.projects).toBe('Projets');
  });

  test('returns English labels', () => {
    const dict = getDict('en');
    expect(dict.projects).toBe('Projects');
  });

  test('missing key is undefined', () => {
    const dict: any = getDict('fr');
    expect(dict.unknown).toBeUndefined();
  });
});
