# RIE Integration Tests

Please note that the tests for RIE in this directory are slightly different then the normal HMS integration and CT tests.
- All of the tests in this directory are intended to test the functionality of RIE, and not the other way around.
- None of these tests are intended to ever run against a real BMC or system. If there is a test that is intended to be ran against real hardware, then the test is not in the correct location. 

## Unique data integration test
The unique data integration test is used a tool to verify that all of the FRU information (ie Serial Numbers) stored in RIE are properly randomized between different instances of RIE from the same original mockup data.

>**Warning** currently this test finds duplicate FRU information on the same node (not between separate RIE instances) for HSN Nics, as it appears multiple devices under redfish have the same serial number.

**Do not** propagate the design of this test out to other HMS services unless there is good reason to do so. This is an unique test where only two instances of RIE are stood up at a time sequentially, and the test needs to be repeated for each mockup. In the future if more API calls need to be added to this test we should consider moving to Tavern.