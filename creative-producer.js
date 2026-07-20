// creative-producer.js
require('dotenv').config();
const fs = require('fs');

function buildGallery() {
  const gallery = JSON.parse(fs.readFileSync('./config/gallery.json'));
  
  const images = gallery.images.map(img => {
    return {
      id: img.id,
      url: process.env[`${img.id}_URL`] || img.url,
      alt: process.env[`${img.id}_ALT`] || img.alt,
      caption: process.env[`${img.id}_CAPTION`] || img.caption,
      category: img.category,
      gender: img.gender
    }
  });

  fs.writeFileSync('./public/gallery-data.json', JSON.stringify({images}, null, 2));
  console.log(`Gallery updated with ${images.length} images`);
}

buildGallery();