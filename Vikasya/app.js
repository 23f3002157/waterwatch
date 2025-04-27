const express = require("express");
const bodyParser = require("body-parser");
const User = require("./models/User");
const Report = require("./models/Report");
const path = require("path");
const session = require("express-session");
const nodemailer = require("nodemailer");
const multer = require("multer");
const sanitizeHtml = require("sanitize-html");
const dotenv = require("dotenv");
const fs = require("fs");
const ejs = require("ejs");



const app = express();
const PORT = process.env.PORT || 3000;

// Ensure uploads directory exists
const uploadsDir = path.join(__dirname, "public", "uploads");
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

app.use(
  session({
    secret: "vikasyaKey",
    resave: false,
    saveUninitialized: false,
  })
);

const mongoose = require("mongoose");

const mongoURI = process.env.MONGO_URI || "mongodb+srv://nishchal:nishchal123@cluster0.cyj89.mongodb.net/waterwatch?retryWrites=true&w=majority&appName=Cluster0";

mongoose
  .connect(mongoURI, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
  })
  .then(() => console.log("✅Connected to MongoDB Atlas"))
  .catch((err) => console.error("MongoDB connection error:", err));

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

app.use(express.static(path.join(__dirname, "public")));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// Multer setup for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, "public/uploads");
  },
  filename: (req, file, cb) => {
    cb(null, `${Date.now()}-${file.originalname}`);
  },
});
const upload = multer({ storage });

// Authority email mapping
const authorityEmails = {
  contamination: ["waterboard@example.com", "ngo@example.com"],
  leak: ["municipal@example.com"],
  misuse: ["localgov@example.com"],
  scarcity: ["waterdept@example.com"],
};

// Nodemailer setup with MailHog
const transporter = nodemailer.createTransport({
  host: process.env.MAILHOG_HOST || "localhost",
  port: process.env.MAILHOG_PORT || 1025,
  auth: null, // MailHog does not require authentication
});

app.get("/", (req, res) => {
  if (req.session.userId) {
    return res.redirect("/home");
  }
  res.render("login");
});

app.get("/register", async (req, res) => {
  res.render("register");
});

app.get("/login", async (req, res) => {
  res.render("login");
});

app.post("/register", async (req, res) => {
  const { username, email, password } = req.body;
  try {
    const user = new User({ username, email, password });
    await user.save();
    return res.redirect("/");
  } catch (err) {
    console.error(err);
    return res.send("Error registering");
  }
});

app.post("/login", async (req, res) => {
  const { email, password } = req.body;
  try {
    const user = await User.findOne({ email, password });
    if (user) {
      req.session.userId = user._id;
      return res.redirect("/home");
    } else {
      return res.send("Invalid email or password");
    }
  } catch (err) {
    console.error(err);
    return res.send("Error logging in");
  }
});

app.get("/home", (req, res) => {
  if (!req.session.userId) {
    return res.redirect("/");
  }
  res.render("home");
});

app.get("/logout", (req, res) => {
  req.session.destroy(() => {
    res.redirect("/");
  });
});

// Report submission route
app.get("/report", (req, res) => {
  if (!req.session.userId) {
    return res.redirect("/login");
  }
  res.render("report", { emailStatus: null });
});

app.post("/report", upload.single("media"), async (req, res) => {
  if (!req.session.userId) {
    return res.redirect("/login");
  }

  const {
    id,
    type,
    title,
    description,
    'location.lat': lat,
    'location.lng': lng,
    reporter,
  } = req.body;
  const mediaPath = req.file ? `/uploads/${req.file.filename}` : "";

  // Debug: Log incoming form data
  console.log("req.body:", req.body);

  try {
    // Validate location data
    if (!lat || !lng) {
      console.log("Missing location data");
      return res.render("report", { emailStatus: "Missing location data (latitude or longitude)." });
    }

    // Check if report ID is unique
    const existingReport = await Report.findOne({ id });
    if (existingReport) {
      console.log("Duplicate report ID:", id);
      return res.render("report", { emailStatus: "Report ID already exists." });
    }

    // Hard-coded quality and trend data
    const quality = {
      ph: 6.5,
      turbidity: 30,
      contaminants: ["Detergents", "Industrial Waste"],
    };
    const trend = [80, 75, 70, 65, 60, 55, 50];

    // Mock AI verification
    const aiResult = {
      verified: true,
      category: type,
      severity: quality.contaminants.includes("Industrial Waste") ? "High" : "Medium",
    };

    if (!aiResult.verified) {
      console.log("AI verification failed");
      return res.render("report", { emailStatus: "Submission not verified by AI" });
    }

    const report = new Report({
      id,
      type,
      title,
      description,
      location: {
        lat: parseFloat(lat),
        lng: parseFloat(lng),
      },
      status: "reported",
      reporter,
      quality,
      trend,
      mediaUrl: mediaPath,
      userId: req.session.userId,
      emailStatus: "Pending",
    });
    await report.save();
    console.log("Report saved:", id);

    // Trigger email routing
    const sanitizedData = {
      id: sanitizeHtml(id || ""),
      type: sanitizeHtml(type || ""),
      title: sanitizeHtml(title || ""),
      description: sanitizeHtml(description || ""),
      location: {
        lat: parseFloat(lat) || 0,
        lng: parseFloat(lng) || 0,
      },
      status: "reported",
      reporter: sanitizeHtml(reporter || ""),
      quality: {
        ph: quality.ph,
        turbidity: quality.turbidity,
        contaminants: quality.contaminants.map(c => sanitizeHtml(c)),
      },
      trend: trend || [],
      mediaUrl: mediaPath ? `http://localhost:${PORT}${mediaPath}` : "",
      reportedAt: new Date(),
    };

    // Debug: Log sanitizedData
    console.log("sanitizedData:", sanitizedData);

    const reportHtml = await ejs.renderFile(
      path.join(__dirname, "views", "report-template.ejs"),
      { sanitizedData }
    );
    console.log("Rendered HTML:", reportHtml);

    // Plain text fallback
    const plainText = `
Water Issue Report

Report Details
ID: ${sanitizedData.id}
Type: ${sanitizedData.type.charAt(0).toUpperCase() + sanitizedData.type.slice(1)}

Issue Summary
Title: ${sanitizedData.title}
Description: ${sanitizedData.description}

Location
Latitude: ${sanitizedData.location.lat}
Longitude: ${sanitizedData.location.lng}

Reporter Information
Name: ${sanitizedData.reporter}
Reported At: ${sanitizedData.reportedAt.toLocaleString()}

Water Quality
pH: ${sanitizedData.quality.ph}
Turbidity: ${sanitizedData.quality.turbidity} NTU
Contaminants: ${sanitizedData.quality.contaminants.join(", ")}

Trend Data
Values: ${sanitizedData.trend.join(", ")}

Community Water Watch © ${new Date().getFullYear()}
Automated report generated for water issue monitoring.
    `.trim();

    const recipients = authorityEmails[sanitizedData.type] || ["default@example.com"];
    if (sanitizedData.quality.contaminants.includes("Industrial Waste")) {
      recipients.push("urgent@example.com");
    }

    // MIME-structured email
    const mailOptions = {
      from: "no-reply@waterwatch.com",
      to: recipients.join(","),
      subject: `Water Issue Report: ${sanitizedData.title} (${sanitizedData.type})`,
      text: plainText, // Explicit plain text part
      html: reportHtml, // HTML part
      ...(mediaPath && {
        attachments: [
          {
            path: path.join(__dirname, "public", mediaPath),
            cid: "media@waterwatch",
          },
        ],
      }),
    };

    await transporter.sendMail(mailOptions);
    console.log("Email sent to:", recipients);

    await Report.findByIdAndUpdate(report._id, {
      emailStatus: "Sent",
      emailRecipients: recipients,
    });
    console.log("Report updated with email status");

    return res.render("report", { emailStatus: "Report generated and emailed successfully." });
  } catch (error) {
    console.error("Error processing report:", error);
    return res.render("report", { emailStatus: `Failed to process report: ${error.message}` });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});