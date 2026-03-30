Feature: Intelligent Failure Diagnosis
  As a developer
  I want to understand why a test failed immediately
  So that I can fix issues faster

  Scenario: View AI diagnosis with category classification when test fails
    Given I am logged in and have a failing test "Payment Processing" with expected outcome "Payment confirmation message"
    When I run the failing test
    Then I should see the test status is "Failed"
    And I should see a failure category badge "Application Bug"
    And I should see a diagnosis summary
    And I should see a diagnosis explanation containing "payment"
    And I should see a recommendation section
    And I should see a proposed fix section
    And I should see a "Re-run Test" action button

  Scenario: View test design failure and apply AI-suggested fix
    Given I am logged in and have a failing test "Broken Selector Test" with expected outcome "element not found on page"
    When I run the failing test
    Then I should see the test status is "Failed"
    And I should see a failure category badge "Test Design Issue"
    And I should see an "Apply Suggested Fix" button
    And I should see an "Edit Test Manually" link
    When I click "Apply Suggested Fix"
    Then I should be redirected to the test list
    And I should see a flash message "Test steps updated with AI suggestion"
    And the test status should be reset to "Not Run"

  Scenario: View environment failure diagnosis with retry option
    Given I am logged in and have a failing test "Unreachable App Test" with expected outcome "connection refused by server"
    When I run the failing test
    Then I should see the test status is "Failed"
    And I should see a failure category badge "Environment Issue"
    And I should see a diagnosis explanation containing "could not be reached"
    And I should see a "Retry Test" action button
