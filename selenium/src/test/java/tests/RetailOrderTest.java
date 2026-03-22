package tests;

import io.github.bonigarcia.wdm.WebDriverManager;
import org.junit.jupiter.api.*;
import org.openqa.selenium.*;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;
import java.util.List;

@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class RetailOrderTest {

    WebDriver driver;
    WebDriverWait wait;
    String baseUrl = System.getProperty("frontend.url");

    @BeforeEach
    public void setup() {
        WebDriverManager.chromedriver().setup();

        ChromeOptions options = new ChromeOptions();
        options.addArguments("--headless=new");
        options.addArguments("--no-sandbox");
        options.addArguments("--disable-dev-shm-usage");

        driver = new ChromeDriver(options);
        driver.manage().window().setSize(new Dimension(1400, 1000));
        driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(5));
        wait = new WebDriverWait(driver, Duration.ofSeconds(20));
    }

    @Test
    @Order(1)
    public void testLaunchApplication() {
        driver.get(baseUrl);
        System.out.println("Opened URL: " + baseUrl);

        WebElement heading = wait.until(ExpectedConditions.visibilityOfElementLocated(
                By.xpath("//h1[contains(text(),'Retail Order Demo')]")
        ));

        Assertions.assertTrue(heading.isDisplayed(), "Application heading is not displayed");
    }

    @Test
    @Order(2)
    public void testProductsAreLoaded() {
        driver.get(baseUrl);

        wait.until(ExpectedConditions.visibilityOfElementLocated(
                By.xpath("//h2[contains(text(),'Products')]")
        ));

        List<WebElement> productRows = driver.findElements(By.xpath("//table//tbody/tr"));
        Assertions.assertTrue(productRows.size() > 0, "Products table is empty");
    }

    @Test
    @Order(3)
    public void testCreateOrderSuccessfully() {
        driver.get(baseUrl);

        wait.until(ExpectedConditions.visibilityOfElementLocated(
                By.xpath("//h1[contains(text(),'Retail Order Demo')]")
        ));

        WebElement nameInput = wait.until(ExpectedConditions.visibilityOfElementLocated(
                By.xpath("//input[@placeholder='Customer Name']")
        ));
        nameInput.sendKeys("TestUser_" + System.currentTimeMillis());

        WebElement emailInput = driver.findElement(
                By.xpath("//input[@placeholder='Customer Email']")
        );
        emailInput.sendKeys("test" + System.currentTimeMillis() + "@test.com");

        WebElement qtyInput = driver.findElement(
                By.xpath("(//table//tbody/tr)[1]//input[@type='number']")
        );
        qtyInput.sendKeys(Keys.chord(Keys.CONTROL, "a"));
        qtyInput.sendKeys("1");

        WebElement createOrderButton = driver.findElement(
                By.xpath("//button[contains(text(),'Create Order')]")
        );
        createOrderButton.click();

        wait.until(ExpectedConditions.or(
                ExpectedConditions.visibilityOfElementLocated(
                        By.xpath("//*[contains(text(),'Order created successfully')]")
                ),
                ExpectedConditions.visibilityOfElementLocated(
                        By.xpath("//*[contains(text(),'Order Number:')]")
                )
        ));

        String pageSource = driver.getPageSource();

        Assertions.assertTrue(
                pageSource.contains("Order created successfully") || pageSource.contains("Order Number"),
                "Order creation success message was not displayed"
        );
    }

    @Test
    @Order(4)
    public void testValidationWhenCustomerDetailsMissing() {
        driver.get(baseUrl);

        wait.until(ExpectedConditions.visibilityOfElementLocated(
                By.xpath("//h1[contains(text(),'Retail Order Demo')]")
        ));

        WebElement qtyInput = driver.findElement(
                By.xpath("(//table//tbody/tr)[1]//input[@type='number']")
        );
        qtyInput.sendKeys(Keys.chord(Keys.CONTROL, "a"));
        qtyInput.sendKeys("1");

        WebElement createOrderButton = driver.findElement(
                By.xpath("//button[contains(text(),'Create Order')]")
        );
        createOrderButton.click();

        WebElement validationMessage = wait.until(ExpectedConditions.visibilityOfElementLocated(
                By.xpath("//*[contains(text(),'Please enter customer details and select at least one product.')]")
        ));

        Assertions.assertTrue(validationMessage.isDisplayed(), "Validation message for missing customer details not shown");
    }

    @Test
    @Order(5)
    public void testValidationWhenNoProductSelected() {
        driver.get(baseUrl);

        wait.until(ExpectedConditions.visibilityOfElementLocated(
                By.xpath("//h1[contains(text(),'Retail Order Demo')]")
        ));

        WebElement nameInput = driver.findElement(
                By.xpath("//input[@placeholder='Customer Name']")
        );
        nameInput.sendKeys("TestUser_" + System.currentTimeMillis());

        WebElement emailInput = driver.findElement(
                By.xpath("//input[@placeholder='Customer Email']")
        );
        emailInput.sendKeys("test" + System.currentTimeMillis() + "@test.com");

        WebElement createOrderButton = driver.findElement(
                By.xpath("//button[contains(text(),'Create Order')]")
        );
        createOrderButton.click();

        WebElement validationMessage = wait.until(ExpectedConditions.visibilityOfElementLocated(
                By.xpath("//*[contains(text(),'Please enter customer details and select at least one product.')]")
        ));

        Assertions.assertTrue(validationMessage.isDisplayed(), "Validation message for no selected product not shown");
    }

    @AfterEach
    public void teardown() {
        if (driver != null) {
            driver.quit();
        }
    }
}