const functions = require("firebase-functions");
const admin = require("firebase-admin");
const nodemailer = require("nodemailer");
const { join } = require("path");
const fs = require("fs");
const { tmpdir } = require("os");

// Initialize Firebase Admin SDK using default credentials
admin.initializeApp({
  storageBucket: "storage address",
});

// Set up Gmail for sending emails
const emailTransporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: "emailaddress", // Replace with your Gmail address
    pass: "app password", // Replace with your app-specific password
  },
});

// This function listens for a Pub/Sub trigger and sends the latest PDF
exports.sendLatestPdf = functions.pubsub.topic('send-latest-pdf').onPublish(async (message) => {
  const storageBucket = admin.storage().bucket();

  try {
    // Get all files in the "pdf/" folder
    const [allFiles] = await storageBucket.getFiles({ prefix: "pdf/" });
    const pdfFiles = allFiles.filter((file) => file.name.endsWith(".pdf"));

    if (pdfFiles.length === 0) {
      console.log("No PDF files found.");
      return;
    }

    // Find the newest PDF file based on the last updated timestamp
    const newestPdf = pdfFiles.reduce((currentLatest, file) => {
      return file.metadata.updated > (currentLatest.metadata.updated || 0) ? file : currentLatest;
    });

    console.log(`Newest PDF file is: ${newestPdf.name}`);

    // Download the newest PDF to a temporary location
    const temporaryFilePath = join(tmpdir(), newestPdf.name.split("/").pop());
    await newestPdf.download({ destination: temporaryFilePath });
    console.log(`File downloaded to: ${temporaryFilePath}`);

    // Send the PDF as an email attachment
    const emailDetails = {
      from: "emailadress", // Your email
      to: "emailaddress", // Recipient's email
      subject: "Your latest Focus Report",
      text: `Hi there! See your latest Focus Report here:: ${newestPdf.name}`,
      attachments: [
        {
          filename: newestPdf.name.split("/").pop(),
          path: temporaryFilePath,
        },
      ],
    };

    await emailTransporter.sendMail(emailDetails);
    console.log(`Email sent to: ${emailDetails.to}`);

    // Delete the temporary file after sending the email
    fs.unlinkSync(temporaryFilePath);
    console.log("Temporary file deleted.");
  } catch (error) {
    console.error(error);
  }
});
