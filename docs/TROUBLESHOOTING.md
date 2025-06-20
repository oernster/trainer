# 🐛 Troubleshooting

## Common Issues

**Application won't start**
- Check Python version (3.8+ required)
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Ensure config.json exists and is valid JSON
- Check that all required API keys are configured

**No train data displayed**
- Verify Transport API credentials in config.json
- Check internet connection
- Confirm Transport API service status at https://developer.transportapi.com/

**Weather not showing**
- Ensure weather.enabled is true in config.json
- Check location coordinates are valid (latitude: -90 to 90, longitude: -180 to 180)
- Verify internet connection for Open-Meteo API

**Astronomy features not working**
- Verify NASA API key in config.json is valid and properly formatted
- Check that astronomy.enabled is true in configuration
- Ensure NASA API key is valid at https://api.nasa.gov/ (should be 40+ characters)
- Check individual service toggles in astronomy.services (apod, iss, neows, epic)
- Verify location coordinates are valid (latitude: -90 to 90, longitude: -180 to 180)
- Check internet connection for NASA API access
- Review logs for specific NASA API service errors
- Ensure at least one astronomy service is enabled
- Check cache duration and update interval settings

**High CPU usage**
- Reduce refresh frequency in config.json
- Disable unused features (weather, astronomy services)
- Check for memory leaks in logs
- Restart application if needed

**Theme issues**
- Try switching themes with Ctrl+T
- Check display.theme setting in config.json
- Restart application to reset theme state

## Logging

Application logs are written to the console and include:
- API request/response information
- Weather and astronomy data updates
- Error messages with stack traces
- Performance metrics and timing information

## Getting Help

1. Check the [troubleshooting section](#-troubleshooting) above
2. Review the [configuration documentation](CONFIGURATION.md)
3. Check the logs for specific error messages
4. Verify all API keys and credentials are correct
5. Test with minimal configuration (disable weather/astronomy temporarily)

## 📞 Support

For support, please:
1. Check the [troubleshooting section](#-troubleshooting)
2. Review the [documentation](.)
3. Search existing [issues](../../issues)
4. Create a new issue if needed